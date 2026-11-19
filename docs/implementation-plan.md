# Hermes 多 Profile 管理后端 · 实施方案 v2

> 状态：已定稿并实施（阶段 0–9）。本文件由 2026-11-19 的实施方案 v2 重建（原文件随工作区回滚丢失），
> 并补充了阶段 9 的落地方式（`openviking[local-embed]`，无 LLM key）。设计见 [design.md](design.md)，
> Hermes 契约见 [hermes-contract.md](hermes-contract.md)，决策记录见 [adr/](adr/)。


## 已定决策
- **D1 代码管理**：开发期只用本地 git；之后推送到 GitHub 公开仓库 `Huangu0/hermes-fleets`（由维护者推送）。不用 GitHub Actions，本地用 `just check` 和 pre-commit 钩子代替 CI；因为仓库公开，pre-commit 还带密钥/禁入文件扫描（ADR-0003）
- **D2 归属**：只管理本服务建的条目。已有的非托管条目只读上报；遇到同名冲突，plan 报冲突、apply 拒绝
- **D3 拓扑**：与 Hermes 同机部署，直接读写 HERMES_HOME，并通过子进程调用 hermes CLI
- **D4 OV 映射**：一个团队对应一个 OV account，一个 profile 对应一个 OV user
- **模型 key**：阶段 7–8 用 Fake OpenViking 开发。阶段 9 经用户同意改用 `openviking[local-embed]`（本地 embedding 模型），不需要 LLM / embedding key；确需 LLM/VLM 的用例跳过并注明原因

## 我定的默认（写入 docs/adr）
- **目标版本**：Hermes 固定 v0.23.1（commit 3b421578），用 setup-hermes.sh 安装。本服务用独立的 Python 3.12 venv
- **技术栈**：FastAPI、SQLAlchemy 2 + Alembic、SQLite（开 WAL 和外键）、ruamel.yaml、filelock
- **鉴权**：静态 API Key
- **skills 挂载**：共享池按 `<name>@<sha>` 存放；每个 profile 生成一个软链视图目录，挂到 skills.external_dirs
- **密钥**：外部密钥只从环境变量读；本服务生成的密钥（如 OV user key）用 Fernet 加密后存在 SQLite
- **gateway**：apply 后默认只提示重启；契约确认后，再提供手动重启接口

## 测试分层
| 标记 | 内容 | 依赖 |
|---|---|---|
| unit | 纯逻辑 | 无 |
| hermes | 用真实 Hermes 0.23.1 + 临时 HERMES_HOME | 本地已安装 Hermes |
| ovfake | 用 Fake OpenViking | 无 |
| ovreal | 真实 openviking-server 0.5.5 的契约测试 | `FLEET_OV_REAL_URL`（未设置则跳过） |
| e2e | 真实 Hermes + 真实 OpenViking（local-embed）全流程 | `just e2e` 启动/复用真实服务 |

所有任务的通用完成标准：`just check`（ruff + mypy + pytest -m "not e2e"）全绿；有表变更就带 Alembic 迁移；写操作都留审计；单独一个 commit。

## 阶段 0 · 工程基础
- **0.1 本地仓库**：git init、uv 项目、ruff / mypy / pytest 配置、justfile、pre-commit 钩子
  - 验收：`just check` 退出码为 0；commit 时钩子会自动运行
- **0.2 应用骨架**：FastAPI app factory，配置 FLEET_HERMES_HOME / FLEET_DB_URL / FLEET_API_KEY / FLEET_DATA_DIR，提供 /healthz
  - 验收：/healthz 返回 200；缺 API Key 时启动失败并给出明确提示
- **0.3 鉴权与错误体**：Bearer API Key 鉴权，错误体统一为 RFC 7807
  - 验收：401、404、422 三类用例通过
- **0.4 数据层**：SQLAlchemy 2 + Alembic，SQLite 设置相关 PRAGMA
  - 验收：`alembic upgrade head` 和 `downgrade base` 能来回执行；WAL 和外键都已开启
- **0.5 审计**：audit_log 表，用服务层装饰器记录
  - 验收：每个写接口都会产生一条审计，内容包含操作者、对象和 diff 摘要
- **0.6 Hermes 测试底座**：`scripts/install-hermes.sh` 固定 tag 安装；fixture 提供临时 HERMES_HOME 和建 profile 的能力
  - 验收：`pytest -m hermes -k smoke` 能建出 profile，版本断言为 0.23.1

## 阶段 1 · Hermes 契约确认
- **1.1 契约测试**（tests/contract），产出 docs/hermes-contract.md：
  - a. profile 目录结构，以及 config.yaml、.env 的位置
  - b. 写入的 mcp_servers 能被 `hermes mcp list` 识别
  - c. skills.external_dirs 里的 skill 能被 `hermes skills list` 识别，并核实本地同名 skill 优先
  - d. platform_toolsets 的修改能体现在 `hermes tools list`
  - e. mcp_servers 的 env 是否支持 ${VAR} 展开，决定密钥是写 .env 还是写 yaml
  - f. `plugins install openviking --yes-deps --enable` 能非交互启用
  - g. 按 profile 重启 gateway 的命令（S2）
  - 验收：契约测试全绿；没通过的项在 ADR 里写明替代方案

## 阶段 2 · Hermes 适配层
- **2.1 CLI 执行器**：不经过 shell，注入 HERMES_HOME 和 -p，带超时，输出结构化错误
  - 验收：命令超时和非 0 退出码都能映射到明确的错误类型
- **2.2 Profile 适配**：list / create / clone / delete，并校验名称
  - 验收：通过 API 建出的 profile 在 `hermes profile list` 里可见；删除后不再可见
- **2.3 YAML 存储**：ruamel 往返读写，只改托管键；先写临时文件再 rename，按 profile 加 filelock，写前备份
  - 验收：非托管内容逐字节不变；两个并发写入不丢更新；注入写入失败时原文件保持不变
- **2.4 .env 托管块**：用标记行包住托管变量
  - 验收：重复写入结果幂等；用户手写的行保留；文件权限为 600
- **2.5 归属台账**：owned_entry 表，记录 profile、类型、名称和内容哈希
  - 验收：增删条目时台账同步更新；能识别出“托管但被手改”的条目
- **2.6 实际状态读取**：输出 ActualProfileState，每个条目标注为 托管 / 非托管 / 托管已改
  - 验收：快照测试通过

## 阶段 3 · 能力目录
- **3.1 Skill 注册**：支持 git url + ref（解析成 sha）或本地路径；校验 SKILL.md 的 frontmatter
  - 验收：用本地 git 仓库做夹具；同一个 sha 不重复拉取；坏 skill 被拒绝
- **3.2 Skill 视图**：为每个 profile 生成软链目录，只包含它被选中的 skill 版本
  - 验收：`hermes -p X skills list` 显示的正好是被选中的那几个
- **3.3 MCP 目录**：用 Pydantic 定义 stdio / http 两种 schema；密钥只能写成 ${SECRET} 引用
  - 验收：写明文密钥被拒绝
- **3.4 Toolset 目录**：从 `hermes tools list` 同步过来，只读
  - 验收：与 CLI 输出一致
- **3.5 Secret 引用**：外部密钥走环境变量，内部密钥用 Fernet 加密存储
  - 验收：在所有接口响应和日志里都搜不到密钥值

## 阶段 4 · 能力集与绑定
- **4.1 Capability Set**：增删改查，每次修改生成不可变的 revision
  - 验收：能按 revision 查到历史版本
- **4.2 Binding**：profile 绑定能力集（可以锁定 revision），并支持 allow / deny 覆盖
  - 验收：CRUD 和约束测试通过
- **4.3 Resolver**：纯函数
  - 验收：属性测试覆盖 deny 优先、缺凭据报错、同输入同输出
- **4.4 冲突规则（D2）**：期望条目和非托管条目同名时，产出冲突
  - 验收：冲突能出现在 resolve 结果里

## 阶段 5 · 对账（M1 完成点）
- **5.1 Plan**：输出结构化的 add / update / remove 操作，加上冲突和缺失凭据
  - 验收：apply 之后再 plan，结果为空
- **5.2 Apply**：支持 dry-run；按 profile 加锁；写 apply_run 记录和备份
  - 验收：中途失败时，所有文件都回到 apply 前的状态
- **5.3 回滚**：按 apply_run 的备份还原
  - 验收：还原后文件哈希与 apply 前一致
- **5.4 漂移检测**
  - 验收：手改 config.yaml 后，drift 能报出具体的键
- **5.5 生效提示**：响应里带 restart_required；契约 1.1g 通过后，再加重启接口
  - 验收：改 MCP 后，restart_required 为 true
- **5.6 M1 端到端脚本**：`just e2e-m1`。流程：建 2 个 profile → 绑一个共享能力集 + 一个私有 skill → apply → 用 hermes CLI 核对 → 手改 → 检测漂移 → 回滚
  - 验收：脚本退出码为 0

## 阶段 6 · 探测
- **6.1 MCP 探测**：调用 `hermes -p X mcp test <name>`，带超时；用一个本地 stdio 回显 server 做夹具
  - 验收：可用和不可用两种 server 的结果都正确
- **6.2 Readiness**：汇总 MCP、凭据、skill 挂载以及 skill 被本地同名覆盖的情况
  - 验收：任一项失败，readiness 为 false，并给出原因

## 阶段 7 · OpenViking 记忆（无 key 开发）
- **7.1 OV 适配接口 + Fake**：Fake 模拟 account、user、key、ACL、资源的语义
  - 验收：适配接口的单测在 Fake 上通过
- **7.2 调研 S4**：openviking-server 不配模型时，能否启动并提供 Admin 和 ACL 接口
  - 验收：结论写入 ADR；如果能启动，就加一组真实服务的契约测试
- **7.3 身份开通**：profile 对应 OV user，生成的 key 加密存储
  - 验收：在 Fake 上重复开通保持幂等；删除 profile 时吊销对应的 user
- **7.4 记忆配置下发**：期望状态里加入 memory 段，apply 时安装并启用插件，写 memory.provider 和 OPENVIKING_ENDPOINT / API_KEY
  - 验收：`hermes -p X plugins list` 显示插件已启用；配置键正确；再次 plan 为空

## 阶段 8 · 知识库（无 key 开发）
- **8.1 知识库增删改查**：一个知识库对应 `viking://resources/<kb>/`
  - 验收：在 Fake 上通过
- **8.2 授权**：按 profile 授予 read / write ACL
  - 验收：在 Fake 上，有授权能读，没授权会被拒
- **8.3 资源导入**：走 add_resource，异步轮询任务状态
  - 验收：成功和失败两种状态都能正确反映

## 阶段 9 · 最终联调（openviking[local-embed]，无模型 key）
- **9.1 起真实服务**：`scripts/ov-up.sh` 在工作区 venv 安装 `openviking[local-embed]==0.5.5`，以 api_key 模式后台启动（冷启动可能需数分钟；不要与 `just check` 并发跑，曾被 OOM kill）
  - 验收：健康检查通过
- **9.2 记忆隔离**：profile A 写入的记忆，B 检索不到
- **9.3 知识库权限**：有授权的 profile 能检索到资源，没授权的检索不到
- **9.4 全量回归**：`just e2e` 全绿（含 `ovreal` 契约测试、已索引 KB 目录上的 ACL、记忆隔离、KB 可见性、完整流程）

## 里程碑
- **M1** = 阶段 0–5：skills、MCP、toolsets 的集中管理与对账
- **M2** = 阶段 6–7：探测与记忆
- **M3** = 阶段 8–9：知识库与联调
- **人工介入点**：阶段 9 已改为 local-embed，无需输入 key；1.1 或 7.2 的调研结论如果推翻了某个默认，我会先停下来问你

---

## 附录 A · 零决策实施评估（2026-11-19，v1 方案上做出，结论已并入 v2）


## 结论
- **M1（skills / MCP / toolsets 对账）**：答完 D1–D3 后可以零决策实施
- **M2 / M3（OpenViking）**：还需要 D4 和一个 embedding 模型的 API key

## 必须你拍板
| # | 决策 | 阻塞 | 我的建议 |
|---|---|---|---|
| D1 | GitHub 仓库的 owner、名称、是否私有 | T0.1，连带全部 | 私有仓库 |
| D2 | profile 里已有、但不是本服务建的 MCP / skills 怎么处理 | T1.2、T4 | 只管自己建的条目，其余只读上报 |
| D3 | 部署拓扑 | 整体架构 | 与 Hermes 同机，直接读写 HERMES_HOME |
| D4 | OpenViking 身份映射 | T6.1 | 一个 profile 对应一个 OV user |

**外部输入**：OpenViking 需要的 embedding 模型 API key，可能还需要一个用于记忆抽取的 LLM key（阻塞 T6.0）。

## 我可以自定的默认（写入 ADR）
- 包名和目录结构
- skills 用 skills.external_dirs 挂载共享池
- toolset 只管绑定里写明的平台
- 服务鉴权用静态 API Key，开发期密钥只从环境变量来
- apply 后只提示重启，不自动重启 gateway

## 沙箱实测（v0.23.1）
- **不能 pip 安装**：setup.py 主动拦截打包，只能用 setup-hermes.sh、Docker 或 Nix。它自带 Python 3.14，所以本服务要单独建 venv，通过子进程调用 CLI。T0.4 已改成用脚本安装
- **测试隔离可行**：把 HERMES_HOME 指向临时目录后，`profile create` 可以非交互执行，`hermes -p <p> config set mcp_servers...` 也能正确写入该 profile 的 config.yaml
- **S1 已解决**：openviking 插件装在 `profiles/<p>/plugins`，按 profile 隔离。非交互启用要加 `--yes-deps --enable`，否则会保持禁用
- **仍待验证**：S2，按 profile 重启 gateway 的方式

## 剩余风险
- Hermes 更新很频繁（11 月中每天都有 canary），配置键可能变化。需要锁定 tag，并在 CI 里跑契约测试
- OpenViking 是 AGPL-3.0，正式上线前请法务确认