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
以后修改文件后，在终端中执行以下三步即可：

  # 1. 将修改的文件加入暂存区
  git add <文件名>
  # 或一次性添加所有修改：
  git add .

  # 2. 提交
  git commit -m "描述你改了什么"

  # 3. 推送
  git push
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
