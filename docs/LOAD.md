# Load：数据落地、结构序列化与导出（pickle/JSON）

## 1. 功能简介

**Load 节点**作为整个数据流最后一环，负责将结构化和标准化后的订单数据（表格、meta、比对结果）进行持久化存储，以及输出为标准 JSON 格式，便于后续数据库入库或联动自动化业务。支持 pickle 二进制缓存（中间态）及标准 JSON 导出，非常适合 ETL/n8n 及 API 返回等多元场景。

---

## 2. 主要流程 & 支持格式

- **中间结果序列化**：采用 pickle 进行二进制持久化（适合短期缓存、跨步持传）
- **最终标准输出**：归集成统一、易查阅、易落库的 JSON 结构 — 包括订单头信息、全量品项、比对分数与总金额

---

## 3. 典型支持方法说明

```python
def write_pkl(dfs, filename):
    # 将中间 DataFrame、dict 等直接存储到本地二进制文件
```
```python
def read_pkl(filename):
    # 恢复上一步缓存的数据
```
```python
def convert_to_json(ordermeta, df, matched_df):
    """
    将订单元信息、明细表（DataFrame）、模糊比对输出合并为标准 JSON 数据
    - 合计金额（prices）
    - orders meta
    - items: 产品ID、对齐品名、原始输入、数量、比对分数
    """
```

### JSON 输出结构举例

```json
{
  "prices": 10000.0,
  "客户名": "测试公司",
  "order_date": "2025-03-25",
  "items": [
    {
      "product_id": "X3212",
      "matched_name": "标准品A",
      "original_input": "A-abc牌",
      "quantity": 2.0,
      "match_score": 0.95
    },
    ...
  ]
}
```

---

## 4. Load HTTP 接口建议

便于 n8n 流程集成，推荐暴露 `/load` POST 接口，实现本地缓存、最终导出 JSON 两类模式。

### a) 订单落地接口

- 路径示例：`/load`
- 方法：POST
- POST body 示例：

```json
{
  "pickle_path": "./tmp/xxxx.pkl",
  "save_json_path": "./results/order_xxxx.json"
}
```

- 处理逻辑：
  1. 用 `read_pkl` 读取前一步 pickle 中的全量对象（如 ordermeta、主df、matched_df）
  2. 用 `convert_to_json` 生成标准订单 JSON
  3. 落盘保存到指定路径，或直接 return JSON

- 返回值：  
  - 成功状态说明  
  - 导出文件路径/JSON 结构体

---

## 5. 用途拓展

- 适用于订单入库、财务流、第三方接口对接，也可中转供下游 AI 流程直接 consume。
- pkl 方式支持任意类型暂存，中间变量复用、断点重算。
- JSON 输出完全对标各类入库 Schema，可衔接 SQL/NoSQL/消息队列。

---

## 6. 依赖环境

- Python >= 3.11
- pandas, pickle, json
- 下游 DB/接口对接建议见主项目文档
