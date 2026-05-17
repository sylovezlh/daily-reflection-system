# Git 推送全新项目至 GitHub 指南

## 前置条件

- 已安装 Git：`git --version`
- 已在 GitHub 创建空仓库（不要勾选 README、.gitignore、License）

## 步骤

### 1. 进入项目文件夹

```bash
cd /path/to/your-project
```

### 2. 初始化 Git 仓库

```bash
git init
```

### 3. 创建 .gitignore（可选，排除不需要上传的文件）

```bash
echo "*.log
__pycache__/
.env" > .gitignore
```

### 4. 将所有文件加入暂存区

```bash
git add .
```

### 5. 创建第一次提交

```bash
git commit -m "初始化项目"
```

### 6. 添加远程仓库

```bash
git remote add origin https://github.com/用户名/仓库名.git
```

### 7. 推送至 GitHub

```bash
git push -u origin main
```

> 如果你的默认分支是 `master`，将 `main` 替换为 `master`：
> ```bash
> git push -u origin master
> ```

---

## 后续日常推送

```bash
cd /path/to/your-project
git add .
git commit -m "描述你改了什么"
git push
```

第一次设置 `-u origin main` 后，后续只需 `git push` 即可。

---

# Git 修改回滚指南（后悔药）

## 先理解 Git 的三个"区域"

在你学会回滚之前，先花一分钟理解 Git 的工作方式。你的文件在 Git 中有**三种状态**，就像三个盒子：

```
[工作区]  ──git add──▶  [暂存区]  ──git commit──▶  [本地仓库]  ──git push──▶  [GitHub]
 你的文件              准备提交的文件           已提交的版本              远程仓库
```

- **工作区**：你正在编辑的文件，改了但 Git 还不知道
- **暂存区**：你已经 `git add` 了，告诉 Git"这些改动我打算提交"
- **本地仓库**：已经 `git commit` 了，改动被永久记录
- **GitHub（远程）**：已经 `git push` 了，改动已经上传到网上

**回滚的本质，就是根据你当前走到了哪一步，往后退。**

---

## 情况一：刚改了文件，还没执行 `git add`

你修改了 `server.py`，但还没做任何 Git 操作。这时改得不对，想恢复到修改前的样子。

### 撤销单个文件

```bash
git restore server.py
```

### 撤销所有改过的文件

```bash
git restore .
```

### 到底发生了什么？

Git 把 `server.py` 恢复到了"上一次 commit 时的样子"。你刚才做的修改全部消失，文件回到修改前的状态。

### 举例

```
你修改了 server.py，把端口从 5000 改成了 8080
然后后悔了，觉得还是 5000 好

➜ git restore server.py
→ server.py 变回修改前的样子，端口回到 5000
```

---

## 情况二：已经 `git add` 了，但还没 `git commit`

你执行了 `git add server.py`，把它放进了暂存区。然后发现不该加这个文件，或者里面的改动有问题。

### 第一步：把文件从暂存区撤回来

```bash
git restore --staged server.py
```

执行完这行后，`server.py` 回到"工作区"状态，相当于你还没 `git add` 过它。

### 第二步：撤销文件本身的修改

```bash
git restore server.py
```

### 如果你想一次性撤销所有文件

```bash
git restore --staged .      # 所有文件退出暂存区
git restore .               # 所有文件恢复到修改前的样子
```

### 到底发生了什么？

第一步：文件从"暂存区"退回"工作区"（Git 不再打算提交它了）
第二步：文件内容本身也恢复到上次 commit 时的样子

### 打个比方

你想寄一个快递：
1. 你把东西放进包装盒（= 修改文件）
2. 你贴上了快递单（= `git add`，东西进了暂存区）
3. 你后悔了，不想寄了
4. 撕掉快递单（= `git restore --staged`，退出暂存区）
5. 把东西拿出来放回原位（= `git restore`，恢复原文件）

---

## 情况三：已经 `git commit` 了，但还没 `git push`

你已经提交了，但改动还在本地，没传到 GitHub。这时有两种选择：

### 选项 A：撤销 commit，但保留你修改的内容（推荐）

```bash
git reset --soft HEAD~1
```

执行后：
- 这个 commit 被撤销了
- 你修改过的文件内容还在（回到了暂存区）
- 你可以改一改，然后重新 `git commit`

> `HEAD~1` 的意思是"回退 1 个 commit"。`HEAD` 代表当前的最新 commit，`~1` 代表往前数 1 个。

### 选项 B：撤销 commit，并且彻底丢弃所有修改

```bash
git reset --hard HEAD~1
```

执行后：
- 这个 commit 被撤销了
- 你修改过的文件内容也全部消失了，回到上一个 commit 的状态

> **这是一个危险命令！** 用了之后修改就找不回来了。除非你完全确定不要这些改动了。

### 两个选项的区别

| 命令 | commit 还在吗 | 修改的文件还在吗 |
|------|:---:|:---:|
| `git reset --soft HEAD~1` | 撤销了 | 保留了 |
| `git reset --hard HEAD~1` | 撤销了 | 也丢了 |

### 举例

```
你 commit 了 3 个文件：a.html, b.html, c.html
push 之前发现 b.html 改错了

➜ git reset --soft HEAD~1
→ commit 撤销了，3 个文件的修改回到暂存区
→ 你用 git restore --staged b.html 把 b.html 撤出暂存区
→ 用 git restore b.html 恢复 b.html
→ 重新 git add a.html c.html
→ 重新 git commit -m "只提交 a 和 c"
```

### 如果 commit 了多次，想回退更多？

```bash
git reset --soft HEAD~3    # 回退最近 3 个 commit，保留修改
```

---

## 情况四：已经 `git push` 到 GitHub 了

改动已经上传到 GitHub。这时**不要用 `reset`**，因为别人可能已经拉取了你的代码。用安全的 `revert`：

### 撤销最近一次 push 的改动

```bash
git revert HEAD
git push
```

### 到底发生了什么？

`git revert` 不会删除历史。它会在原来的基础上创建一个**新的 commit**，这个新 commit 的内容正好和上一个 commit "相反"——把改过的东西改回去。然后 `git push` 把这个"反向 commit"上传到 GitHub。

### 为什么不用 reset？

```
reset：  A → B → C → (删除C)    历史被改写了，如果别人已经下载了C就会出问题
revert： A → B → C → D(反向C)    历史完整，所有人都能看到"C 被撤销了"
```

### 举例

```
你 push 了一个 commit，把所有文字改成了红色
然后觉得太丑了，想改回去

➜ git revert HEAD
→ 创建一个新 commit："Revert '把所有文字改成红色'"
→ 这个新 commit 的内容就是把红色改回去

➜ git push
→ 上传到 GitHub，所有人都看到红色被改回去了
```

---

## 速查表

| 你做了什么 | 想撤销，用这个命令 |
|-----------|-------------------|
| 改了文件，没 `git add` | `git restore <文件名>` |
| `git add` 了，没 `git commit` | `git restore --staged <文件名>` 然后 `git restore <文件名>` |
| `git commit` 了，没 `git push`，想保留修改 | `git reset --soft HEAD~1` |
| `git commit` 了，没 `git push`，修改也不要了 | `git reset --hard HEAD~1` |
| `git push` 了，改动在 GitHub 上了 | `git revert HEAD` 然后 `git push` |

---

## 总结一句话

**改到哪一步了，就往后退一步。推到网上了就别删历史，用 `revert` 留个记录。**
