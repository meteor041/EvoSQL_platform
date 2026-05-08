# EvoSQL 严格实现重构执行计划

## 目标
将当前最小可运行版升级为更严格的 EvoSQL 流程实现，并为每个阶段补充可自动验证的测试。

核心能力：

1. 显式构建和记录 `C^(0)` 与每轮 `C^(t)`
2. 多轮候选采样、列级上下文演化和语义锚点注入
3. 严格区分 `SCR` 与 `ECA` 两类 refinement
4. 基于运行时信号的 adaptive scheduler 与 early-stop
5. 最终候选池统一重排、置信度拆解和可解释决策
6. 前端展示上下文、簇、分数和最终决策依据

---

## 执行原则

1. 保持现有 API 尽量兼容，新增字段以可选结构返回。
2. 后端主流程优先保证结构正确，再优化模型效果。
3. 每个阶段都写测试脚本或测试用例覆盖验收标准。
4. Mock/真实模型路由保留给演示与本地测试，但 EvoSQL 主流程不依赖 mock 特判。
5. 每次文件修改后提交 git。

---

## 阶段 A：上下文结构重构

状态：待完成

### 实现任务
1. 扩展 `ContextState`：
   - `semantic_anchors`
   - `iteration`
2. 扩展 trace/result：
   - 每轮上下文摘要
   - schema 表列摘要
   - anchors/hints 数量
3. 显式构造 `C^(0)`：
   - `C^(0)` 包含完整 schema、外部知识、问题和初始 instruction
   - schema linking 作为 `C^(0) -> C^(1)` 的预处理 trace 记录
4. `EvoSqlEngine.run()` 每轮使用 `ContextState` 演化，而不是只维护独立变量。

### 验收
- 返回结果中能看到 `C^(0)` 和每轮 `C^(t)` 的结构摘要。
- 测试覆盖上下文初始化与 trace 输出。

---

## 阶段 B：SCR 列级重构

状态：待完成

### 实现任务
1. 从候选池解析引用表和引用列。
2. 对表列做 union 聚合。
3. 支持表级和列级 schema 裁剪。
4. 显式清空：
   - `history_hints`
   - `semantic_anchors`
5. 输出新的 `C^(t+1)` 与 refinement 详情。

### 验收
- SCR 后 schema 能缩减到表列级。
- trace 中能看到保留表、保留列和提示清空结果。
- 测试覆盖 SCR 的列级 union 与上下文重置。

---

## 阶段 C：ECA 簇与语义锚点重构

状态：待完成

### 实现任务
1. 统一候选执行结果摘要：
   - 行数
   - 列集合
   - 前几行摘要
   - 聚合特征
2. 按结果一致性聚类。
3. 保留 Top-k 高一致性簇。
4. 从簇代表构造语义锚点：
   - SQL
   - execution signature
   - result summary
   - referenced tables/columns
5. 将语义锚点注入下一轮上下文。

### 验收
- ECA 输出簇、保留簇和 anchors。
- 下一轮上下文能读取 anchors。
- 测试覆盖聚类、Top-k 和锚点内容。

---

## 阶段 D：调度器与 early-stop 重构

状态：待完成

### 实现任务
1. 调度输入增加运行时信号：
   - 问题复杂度
   - schema 规模
   - 候选执行成功率
   - 候选分歧程度
   - 空结果比例
2. 动态调整：
   - 最大轮数
   - 每轮采样数
   - ECA top-k
3. early-stop 增加多因素判断：
   - schema 是否稳定
   - cluster signature 是否稳定
   - best SQL 是否稳定
   - 连续失败轮数

### 验收
- scheduler 能根据运行时指标调整后续采样。
- early-stop 不只依赖表集合。
- 测试覆盖收敛停止和失败提前终止。

---

## 阶段 E：score 与最终选择重构

状态：待完成

### 实现任务
1. 候选分数拆为：
   - `prior_score`
   - `schema_score`
   - `structure_score`
   - `execution_score`
   - `consistency_score`
   - `final_score`
2. 结构分覆盖：
   - 聚合需求
   - top-k/ranking 需求
   - 趋势问题时间分组
   - join 路径合理性
3. 执行分覆盖：
   - 是否执行成功
   - 是否空结果
   - 是否与主簇一致
4. 最终选择：
   - 优先主一致性簇
   - 再按 `final_score`
   - 同分时按多数一致性和候选先验
5. 返回最终决策说明。

### 验收
- 每个候选都有 score breakdown。
- 最终 SQL 有结构化 selection rationale。
- 测试覆盖打分与最终选择。

---

## 阶段 F：前端可解释性同步升级

状态：待完成

### 实现任务
1. 展示每轮上下文卡片：
   - schema subset
   - semantic anchors
   - history hints
2. 展示每轮簇视图。
3. 展示 score breakdown。
4. 展示最终决策说明。

### 验收
- 页面能展示完整 EvoSQL 过程面板。
- 前端静态编译检查通过。

---

## 测试计划

1. Python 单元测试：`pytest`
2. 指定解释器回归：`E:\anaconda3\python.exe -m pytest`
3. 前端 SFC 编译检查：使用 `@vue/compiler-sfc`，不执行 `npm run build`

---

## 当前执行顺序

1. 阶段 A 和 B：上下文演化 + SCR 列级裁剪
2. 阶段 C：ECA 聚类与 anchors
3. 阶段 D 和 E：scheduler、early-stop、score、最终选择
4. 阶段 F：前端过程可视化
5. 全量测试和提交
