# AstrBot Plugin - 永劫无间教学助手 (Naraka Tutor)

[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3Dv3.4-blue)](https://github.com/Soulter/AstrBot)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个基于 **AstrBot** 框架的 QQ 群聊机器人插件，专为《永劫无间》游戏技巧教学设计。插件通过 RAG（检索增强生成）技术，将本地 PDF 教学材料构建为向量知识库，在用户 **@机器人 + 自然语言提问** 时，自动检索相关材料并调用 LLM 生成准确回答。

---

## ✨ 功能特性

- **@触发 RAG 问答**：群聊中 @机器人 并提问，自动判断是否涉及永劫无间，智能调取知识库。
- **本地 PDF 知识库**：支持将任意数量的 PDF 教学文档放入 `materials/` 目录，自动解析、分块、向量化。
- **零打扰设计**：不满足触发条件（未 @ 或未命中关键词）时，不影响机器人原有对话流程。
- **轻量 Embedding**：基于 `chromadb` 默认 ONNX 向量模型，无需 PyTorch/CUDA，CPU 即可运行。
- **可配置提示词**：支持自定义 RAG 注入模板，灵活控制 LLM 的回答风格与约束。
- **热重载支持**：提供 `/naraka_reload` 管理员命令，可随时更新 PDF 后重建知识库。

---

## 📦 安装方法

1. 确保你已部署 [AstrBot](https://github.com/Soulter/AstrBot) 并接入 NapCat（QQ）与 LLM。
2. 将本插件文件夹（`astrbot_plugin_naraka_tutor/`）整体复制到 AstrBot 的插件目录：
   ```
   AstrBot/data/plugins/astrbot_plugin_naraka_tutor/
   ```
3. 确保 `materials/` 目录中已放入你的永劫无间 PDF 教学文件。
4. 重启 AstrBot，或在 WebUI 中点击 **"重载插件"**。
5. 插件会自动安装依赖并构建向量知识库（首次加载可能需要数秒到数分钟，取决于 PDF 页数）。

---

## ⚙️ 配置说明

插件使用 AstrBot 官方配置系统，配置项位于 `_conf_schema.json`，可在 WebUI **插件配置** 页面直接修改：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `trigger_keywords` | list | 详见代码 | 触发 RAG 的关键词列表。消息中包含任意一词即检索。 |
| `top_k` | int | `5` | 每次检索返回的最相关文本块数量。 |
| `chunk_size` | int | `512` | PDF 文本分块大小（字符数）。 |
| `chunk_overlap` | int | `64` | 相邻文本块的重叠字符数，保证上下文连贯。 |
| `system_prompt_template` | string | 详见代码 | 注入 LLM 的上下文模板，可用 `{context}` 和 `{question}` 变量。 |

---

## 🚀 使用方式

在已启用机器人的 QQ 群中，直接发送：

```
@机器人 太刀怎么振刀？
```

或：

```
@机器人 解释下跑蓄和目押
```

机器人将：
1. 检测到你 @ 了它。
2. 判断问题命中永劫无间关键词。
3. 从向量库检索最相关的教学片段。
4. 将片段注入 LLM 上下文，生成基于教材的准确回答。

---

## 🛠️ 管理员命令

| 命令 | 权限 | 说明 |
|------|------|------|
| `/naraka_reload` | ADMIN | 清空向量库并重新解析 `materials/` 下所有 PDF。 |
| `/naraka_status` | ALL | 查看当前知识库状态（PDF 数、向量记录数、配置参数）。 |

---

## 📁 目录结构

```
astrbot_plugin_naraka_tutor/
├── main.py                 # 插件主入口（事件拦截、命令注册）
├── _conf_schema.json       # AstrBot 配置模式定义
├── metadata.yaml           # 插件市场元数据
├── requirements.txt        # Python 依赖
├── LICENSE                 # MIT 许可证
├── README.md               # 本文件
├── .gitignore              # Git 忽略规则
├── rag_engine/             # RAG 核心模块
│   ├── __init__.py
│   ├── pdf_parser.py       # PDF 解析（PyMuPDF）
│   ├── vector_store.py     # 向量存储（ChromaDB）
│   └── utils.py            # 文本清洗与分块工具
└── materials/              # 教学材料目录
    ├── README.md
    └── *.pdf               # 用户提供的永劫无间 PDF
```

---

## ⚠️ 注意事项

1. **依赖安装**：首次启用插件时，AstrBot 会自动读取 `requirements.txt` 并尝试安装 `pymupdf` 和 `chromadb`。如果网络不佳，可能需要手动进入 AstrBot 环境安装。
2. **首次构建时间**：PDF 页数较多时，首次构建向量库可能需要一定时间，请查看 AstrBot 控制台日志了解进度。
3. **编码问题**：本插件使用 PyMuPDF 提取 PDF 文本，对大多数中文 PDF 兼容性良好。若遇到乱码，请检查 PDF 是否为扫描版图片（扫描版需 OCR，本插件暂不支持）。
4. **LLM 回答风格**：若希望机器人回答更严格或更口语化，可修改 `system_prompt_template` 配置项。

---

## 🤝 贡献

欢迎提交 Issue 或 Pull Request。如果你有任何改进建议（如支持更多文件格式、更好的分块策略、关键词语义扩展等），请随时交流！

---

## License

[MIT](LICENSE)
