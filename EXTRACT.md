# PaddleOCR表格抽取与ETL接口说明

## 简介

本项目提供了**基于PaddleOCR与Paddlex的图片/PDF表格自动识别与结构化提取工具**。用户可直接将图片或PDF文档发送至FastAPI接口，自动获得结构化表格及订单头信息，便于后续存储、数据分析和ETL自动化流程（如n8n流程编排）。

## 主要功能/流程

- **Extract (提取):**
  - 支持上传 PDF 或图片文件。
  - 自动区分图片和PDF等文件类型。
  - 使用 PaddleOCR/Table OCR 自动识别表格及表单头部（如订单号、下单日期、买方名称）。
  - 返回结构化 dataframes，可直接用于ETL。
- **Transform (转换):**
  - 表格内容支持进一步数据规范化、字段补全、格式清洗等（详见transform示例）。
- **Load (加载):**
  - 返回DataFrame结构(JSON格式)，也支持存储为parquet、csv等文件格式，便于与n8n、数据仓库等集成。

## 主要接口

### 1. 图片表格接口

```python
def img_to_dataframes_paddle(img_path: Union[str, bytes]) -> pd.DataFrame:
    """
    识别图片中的表格内容，输出pandas DataFrame。
    - 输入: 图片路径或图片二进制流
    - 输出: 表格结构DataFrame，每行为一个OCR识别结果
    """
```

### 2. PDF表格及订单头信息接口

```python
def pdf_to_dataframes_paddle(pdf_path: str) -> pd.DataFrame:
    """
    识别PDF中的表格和发票/订单头信息。
    - 输入：PDF文件路径  
    - 输出：表格结构DataFrame，每行为订单/发票表格数据，并自动补充订单头字段。
    """
```

## FastAPI demo接口示例

- **/extract**
    - 上传文件，自动识别、提取表格内容及单头信息
    - 返回标准JSON（list of dict），适合n8n等自动化平台后续处理

## 环境依赖

- python >= 3.11
- paddlex, pandas, fastapi, uvicorn
- paddleocr
