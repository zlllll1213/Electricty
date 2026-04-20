# 国家电力预测平台

一个面向国家级月度用电数据的全栈预测与分析应用，当前已经从 `Streamlit` MVP 重构为 `FastAPI + React + Vite` 架构，并主动对齐未来并入 `AKTNL/PowerModel` 的模块化方式。

## 技术栈

- Backend: `FastAPI`, `Pydantic`
- Forecasting: `pandas`, `statsmodels`, `scipy`
- Frontend: `React 19`, `Vite`, `Plotly`
- LLM Access: OpenAI-compatible `/chat/completions`

## 当前能力

- 加载仓库内置的国家能源局真实公开月度数据
- 上传并校验同结构 CSV
- 对月度数据做清洗、插值补齐和基础统计
- 使用 SARIMA 预测未来 6 到 12 个月的全国全社会用电量
- 生成本地规则报告，并支持云端模型润色
- 提供规则问答，并支持云端模型增强
- 输出适合 React 直接消费的图表序列和统一 API 响应

## 目录结构

```text
app/
  main.py                # FastAPI 入口
  routers/national.py    # 国家模块 API
  schemas.py             # 请求/响应模型
  services/national.py   # 预测编排与业务逻辑
  state.py               # 运行时配置

frontend/
  src/
    components/          # 复用 UI 组件
    pages/               # 预测、报告、数据页
    lib/api.js           # 前端请求层

src/
  preprocess.py
  forecast/
  analysis/
  llm/
  data_loader.py         # 继续承载核心算法与数据处理逻辑
```

## 快速开始

### 1. 安装后端依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 3. 启动后端

```bash
uvicorn app.main:app --reload
```

后端启动后可访问：

- 首页：`http://127.0.0.1:8000/`
- 健康检查：`http://127.0.0.1:8000/health`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`

### 4. 启动前端开发模式

```bash
cd frontend
npm run dev
```

然后访问：

- `http://127.0.0.1:5173/`

### 5. 构建前端并由 FastAPI 托管

```bash
cd frontend
npm run build
cd ..
uvicorn app.main:app --reload
```

## API 概览

当前国家模块接口如下：

- `GET /api/national/datasets/default`
- `POST /api/national/datasets/validate`
- `POST /api/national/forecast/run`
- `POST /api/national/report/polish`
- `POST /api/national/qa`
- `POST /api/national/llm/test`
- `GET /api/national/meta`

响应统一采用：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

## CSV 数据格式

必填字段：

- `date`
- `consumption_billion_kwh`

可选字段：

- `source`
- `source_url`
- `note`

示例：

```csv
date,consumption_billion_kwh,source,note
2024-01,6900,国家能源局公开统计,根据公开月报整理
2024-02,6200,国家能源局公开统计,根据公开月报整理
```

## 测试

```bash
pytest
```

覆盖范围包括：

- 预处理必填字段与缺失月份补齐
- 样本长度校验
- 默认数据集接口
- 上传数据校验接口
- 预测接口
- 报告润色回退逻辑
- 问答规则回退逻辑

## 与 PowerModel 的未来映射

这个仓库现在的目标不是复制家庭用电产品，而是把“国家级预测”先做成一个独立模块。后续并入 `PowerModel` 时，推荐作为新的国家业务页面接入，保留：

- 独立路由与页面
- 统一的 `code / message / data` 接口风格
- 可复用的图表、报告、问答工作台结构

这样未来可以形成：

- 家庭预测模块
- 国家预测模块
- 共用的前后端基础设施与 LLM 接入方式
