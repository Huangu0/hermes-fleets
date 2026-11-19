# Hermes 多 Profile 管理后端 · 设计 v2

> v1（2026-11-19）是精简架构草案；v2 并入了 D1–D4 决策、开发期 SQLite、Hermes v0.23.1 实测要点。
> 本文件在 2026-11-20 工作区回滚后重建并随代码版本化。实施计划见 [implementation-plan.md](implementation-plan.md)，
> Hermes 契约见 [hermes-contract.md](hermes-contract.md)，具体取舍见 [adr/](adr/)。

## 1. 需求

纯后端，集中管理 hermes-agent 多个 profile 的 skills / MCP servers / toolsets，再扩展为用 OpenViking
管理记忆与知识库。前端后补。不做网关，不代理 MCP 流量，不碰 Agent 运行时。

## 2. 核心思路：期望状态 + 对账（plan / apply）

- DB 存 **期望状态**；`$HERMES_HOME/profiles/<p>/` 是 **实际状态**。
- **Resolver**（纯函数）根据 bindings + catalog 算出每个 profile 的 `DesiredProfileState`；
  **Reconciler** 读实际状态、出结构化 diff（plan），再写入（apply），失败整体回滚。
- 只有 Hermes 适配层能碰 Hermes 文件：单一写入口，漂移可检测（drift）。
- 归属（D2）：只管理本服务写入的条目（`owned_entry` 台账 + 内容哈希）。profile 里已有的非托管条目
  只读上报；同名冲突时 plan 报冲突、apply 拒绝。

## 3. 已定决策

| # | 决策 | 结论 |
|---|---|---|
| D1 | 代码管理 | 本地 git；之后推到 GitHub 公开仓库 `Huangu0/hermes-fleets`。无 GitHub Actions，`just check` + pre-commit 代替 CI；公开仓库 → 提交前密钥扫描 |
| D2 | 非托管条目 | 只管自己建的；其余只读上报；同名冲突 plan 报、apply 拒 |
| D3 | 拓扑 | 与 Hermes 同机，直接读写 `HERMES_HOME`，子进程调用 hermes CLI |
| D4 | OV 身份 | 一个团队 = 一个 OV account；一个 profile = 一个 OV user |

## 4. 技术栈

Python 3.12（服务自身 venv）、FastAPI、Pydantic v2、pydantic-settings、SQLAlchemy 2 + Alembic、
SQLite（WAL + 外键，生产可换 MySQL）、ruamel.yaml（round-trip 保留注释）、filelock、httpx、cryptography(Fernet)。
Hermes v0.23.1 自带 Python 3.14，只能用 tag 的 `setup-hermes.sh` 安装（pip 安装被上游拦截），本服务只通过
`scripts/hermes` 启动器以子进程调用它。

## 5. 分层（单向依赖：api → services → domain / repos → adapters）

```
src/hermes_fleet/
  api/v1/        路由：只做参数与响应（Bearer API Key，RFC 7807 错误体）
  schemas/       Pydantic 契约
  services/      用例编排（profiles、catalog、capability sets、bindings、reconcile、probes、memory、knowledge）
  domain/        纯逻辑：resolver、diff、冲突规则
  repos/         SQLAlchemy 访问（ORM 在 db/models.py）
  adapters/
    hermes/      CLI 执行器、profile API、YAML 存储、托管 .env 块、实际状态读取
    openviking/  httpx 客户端 + Fake 服务器
    mcp/         握手探测（经 hermes mcp test）
  core/          配置、鉴权、日志、错误
  db/            engine、models、alembic 迁移
```

## 6. 模块

1. **profiles**：封装 `hermes profile list/create/delete`（`create` 需 `--no-alias`；clone 用 `--clone-from`，
   与 `--no-skills` 不兼容）。删除 profile 时触发 hooks（吊销 OV 用户、清 KB 授权）。
2. **catalog**
   - skill：git url + ref 解析为固定 sha，或本地路径；校验 `SKILL.md` frontmatter；落到共享池
     `<data>/skill-pool/<name>@<sha>`，同 sha 不重复拉取。
   - mcp_server：stdio / http 两种 schema；密钥只能写成 `${NAME}` 占位，明文被拒。
   - toolset：从 `hermes tools list` 同步，只读镜像。
   - secret_ref：外部密钥来自环境变量；本服务生成的密钥（OV user key）用 Fernet 加密入库；API 永不返回值。
3. **capability_sets**：skills + MCP + toolsets + 所需凭据名打包；每次修改生成不可变 revision。
4. **bindings**：profile ↔ capability_set（可锁 revision）+ allow/deny 覆盖（deny 优先）。
5. **resolver**：纯函数，输出 `DesiredProfileState`（带来源）；缺凭据报错；同输入同输出（hypothesis 属性测试）。
6. **reconcile**：plan（add/update/remove + conflicts + missing secrets）、apply（dry-run、按 profile 文件锁、
   apply_run 记录 + 备份、失败回滚）、rollback（按备份还原，哈希一致）、drift、`restart_required`。
   - skills：每个 profile 一个软链“视图目录”`<data>/skill-views/<p>/`，挂到 `skills.external_dirs`。
   - MCP：`config.yaml` 里保留 `${VAR}` 占位，值写到 profile `.env` 的托管块（Hermes 从 profile .env 展开）。
   - toolsets：`platform_toolsets.<platform>`。
   - memory：`memory.provider: openviking` + `plugins.enabled: [openviking]` + `OPENVIKING_*` 写托管 .env。
7. **probes**：`hermes -p X mcp test <name>`（带超时）+ readiness 汇总（MCP、凭据、skill 挂载、本地同名覆盖）。
8. **memory（OpenViking）**：团队 account 自举；每 profile 幂等开通 OV user 并签发 key（加密存储）；
   删除 profile 时吊销（OV 不可达返回 503，不留活 key）。
9. **knowledge**：一个 KB = `viking://resources/<kb>/`，创建时设为 restricted 且 ACL 为空（resources 根默认全员可读）；
   按 profile 授 read/write；导入走 `add_resource`（URL 或 base64 ≤10 MiB，本地文件先 `temp_upload`），任务轮询。

## 7. API（/v1，Bearer API Key）

- `/v1/profiles`、`/v1/profiles/{p}`
- `/v1/skills`、`/v1/mcp-servers`、`/v1/toolsets`（`POST /v1/toolsets/sync`）、`/v1/secrets`
- `/v1/capability-sets`、`/v1/capability-sets/{name}/revisions/{rev}`
- `/v1/profiles/{p}/bindings`、`/v1/profiles/{p}/overrides`
- `GET /v1/profiles/{p}/plan`、`POST /v1/profiles/{p}/apply`、`GET /v1/profiles/{p}/drift`、
  `POST /v1/apply-runs/{id}/rollback`、`POST /v1/gateway/restart`
- `/v1/profiles/{p}/probes/mcp/{name}`、`/v1/profiles/{p}/readiness`
- `/v1/openviking`（状态与团队账户自举）、`/v1/profiles/{p}/memory`
- `/v1/knowledge-bases`、`/v1/knowledge-bases/{kb}/grants`、`/files`、`/search`、`/imports`
- `/v1/audit`、`/healthz`（免鉴权）

## 8. 数据表

audit_log、managed_profile、owned_entry、skill、mcp_server、toolset、secret_ref、capability_set、
capability_set_revision、profile_binding、profile_override、apply_run、ov_identity、knowledge_base、kb_grant、kb_import。

## 9. OpenViking 映射

- 一个团队 = 一个 OV account（`FLEET_OV_ACCOUNT`），一个 profile = 一个 OV user：记忆与会话天然隔离。
- 共享知识放在 `viking://resources/<kb>/`，用 ACL 按 profile 授权。
- 服务调用 OV 时默认 **不信任** `HTTP(S)_PROXY`（`FLEET_OV_TRUST_ENV=false`）：沙箱代理会对任意 `/health`
  回 200，导致死端点看起来健康（ADR-0016）。

## 10. 风险

- OpenViking 为 AGPL-3.0；以独立 HTTP 服务方式调用、不改代码，上生产前请法务确认。
- Hermes 迭代很快，配置键可能变化：锁定 tag，契约测试（`tests/contract`）随版本升级重跑。
- 配置变更只对新会话生效；gateway 重启是主机级的（`hermes gateway restart --detach`），不能按 profile 重启。
- 真实 OpenViking 冷启动慢（数分钟）、内存占用高；不要和 `just check` 并发跑。
