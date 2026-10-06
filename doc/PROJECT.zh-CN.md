# 项目结构与开发说明（给程序员）

听写 / 拼写练习桌面工具：Python + Tkinter，无 src 布局、无子包，全部为仓库根目录下的平铺模块。

## 运行

```bash
/usr/bin/python3 ctest.py   # macOS 系统 Python 自带 Tkinter
```

- Tkinter **不在 pip 上**。`_tkinter` 缺失时改用 macOS 系统 Python，或 `conda create -n wordreview python=3.11 tk`。
- `requirements.txt` 只有 `pyttsx3`，且**仅 Windows/Linux 需要**；macOS 走 `say` 命令行（`Reader.py`），全新 macOS 环境零安装即可运行。

## 模块划分

`ctest.py` 只是入口（`PracticeApp().mainloop()`，6 行），实际结构：

| 文件 | 职责 |
| --- | --- |
| `app.py` | **主程序**：`PracticeApp(tk.Tk)`，全部 Tk 状态变量、主页界面、文件选择对话框、`speak`（TTS 线程） |
| `practice.py` | **练习流程**：出题界面、提交/结算/保存错题；模式注册表 `MODES` 与 `mode_for_record_kind` |
| `review.py` | **错题复习**：列表筛选（语种 + 日历日期）、删除、复习测验；`language_label` |
| `files.py` | **文件管理**：练习 CSV 加载（`load_exercises`）、错题本读写（`WRONG_FILE`/`load_wrong_entries`/`write_wrong_entries`） |
| `models.py` | 领域数据与判分：`Exercise`、`WrongEntry`、`QuestionView`、`normalise`、`is_correct_answer`、`select_exercise_range` |
| `dictation.py` | **听写**模式：`DictationMode`（`name`/`record_kind`/`auto_play`/`view(...)`） |
| `spelling.py` | **拼写**模式：`SpellingMode`，接口同上 |
| `widgets.py` | 通用控件：`DateField`、`CalendarPopup`（日历选日期） |
| `Reader.py` | TTS 与语言解析：`read_text_aloud`、`canonical_language` |

## 架构要点

- **屏幕是 Mixin，不是独立控件**：`PracticeApp(PracticeMixin, ReviewMixin, tk.Tk)`。状态只定义在 `app.py` 的 `__init__`，mixin 里的方法通过 `self` 访问。切屏方式是 `_clear()` 后重建界面。
- **依赖方向无环**：`models` ← `files` / `dictation` / `spelling` ← `practice` ← `review` ← `app` ← `ctest`。
- **模式对象承载听写/拼写差异**：`mode.view(primary_language, secondary_language, primary_text, listen_hint=...)` 返回 `QuestionView(prompt, display, instruction)`；`display` 为空串表示该行不渲染。练习界面用默认 `listen_hint=True`（听写显示"Listen to…"提示），复习界面传 `False`。`auto_play` 控制是否自动朗读。
- **数据流**：选 CSV（首行=两个语言名）→ 加载练习 → 答错进 `self.wrong_answers` → 结算时 `save_wrong_answers` 追加进 `Wrong.csv` → 复习界面筛选/重测，答对即从文件移除。

## 数据格式

- **练习 CSV**：首行两个语言名（仅 `English`/`French`/`Spanish`/`Chinese`，由 `canonical_language` 校验），之后每行恰好两个非空单元格，按 `utf-8-sig` 读取。
- **`Wrong.csv`** 位于 `Resource/Data/Wrong.csv`（gitignored），表头：
  `Practice time,Practice type,Primary language,Secondary language,Primary text,Correct answer,User answer`。
  练习类型取值是 `DictationMode.record_kind` / `SpellingMode.record_kind`（`"Dictation"` / `"spelling"`），`mode_for_record_kind` 和已有数据都依赖这两个字符串，**不要改名**。该文件**允许手工编辑**：`load_wrong_entries` 会清除格式错误的行（列数不对、时间戳无效、未知练习类型、语言为空或不受支持、题目或答案为空），补回缺失的表头，把清空过的文件重建为只含表头，只要清理过就会立即重写文件；`write_wrong_entries` 会自动创建父目录，因此整个 `Resource/Data` 目录删掉也只会从 0 重建。**无旧格式兼容**：5 列旧行校验不通过，会被清除。每次写入都是整文件重写，新文件带 UTF-8 BOM（Excel 需要，别"修"）。
- **判分**：`is_correct_answer(..., allow_alternatives=True)` 固定启用——`|`/`｜` 分隔可接受答案；比较只折叠空白与英文大小写，**不去**重音/汉字。
- **复习语义**：行的身份 = 它在 `self.all_wrong_entries` 里的下标；答对或删除会把该下标加入 `review_removed` 后整表重写，**不要**用筛选后的子集回写文件。

## 扩展指引

- **新增一屏**：加一个 mixin（或 `PracticeApp` 上的方法），从 `_build_home` 接线。
- **新增练习模式**：新建模块放一个与 `DictationMode` 同接口的类，注册进 `practice.MODES`；如需落库，给它 `record_kind` 并扩展 `mode_for_record_kind`。
- **改界面文案**：注意现有 UI 字体 `("Arial Unicode MS", …)`，中文/法文要保留。
- **TTS**：跑在守护线程（`PracticeApp.speak`），`Reader.read_text_aloud` 吞掉所有异常——语音失败是预期行为，不要当 bug 报。macOS 音色由 `say -v ?` 动态解析并缓存，别硬编码音色名。

## 验证

仓库**没有** linter、formatter、typechecker 或 CI。可用的检查（在仓库根目录运行）：

1. `python -m py_compile *.py`
2. `python -m unittest` —— 纯标准库，无需安装：
   - `test_modules.py` —— 每个模块各开一个全新解释器 import（防止拆分后出现 import 顺序问题或符号缺失），并检查公开符号、`PracticeApp` 的 mixin 组合、听写/拼写模式的统一接口。
   - `test_wrong_entries.py` —— 最脆弱的 CSV 清理行为：坏行清除、旧格式行清除、补表头、删除/清空后从 0 重建、自动创建父目录、UTF-8 BOM、整表往返一致、干净文件不被重写。
3. 手工启动 GUI，用 `Resource/example.csv` 走一遍 Dictation / Spelling / 复习。

脚本化驱动 `PracticeApp` 不需要 mainloop，但**必须先**打补丁 `tkinter.messagebox.showinfo/showerror`，否则弹窗会阻塞。测数据层时 `import files` 后把 `files.WRONG_FILE` 指向临时路径即可（单测就是这么做的）。

## 已知问题

- `README.md` 结尾曾有已提交的合并冲突标记，现已按与 `Reader.py` 一致的一侧解决（中文 `Tingting`、法语/西班牙语 `Eddy` 音色、语速 150）；当时的 stash（`stash@{0}`）仍留在仓库里。
- `.gitignore` 第 4 行忽略了 `.gitignore` 自身，因此忽略规则**不会被提交**，仅在本地生效。

英文版见 `doc/PROJECT.md`。
