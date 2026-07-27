import os

def print_tree(startpath, ignore_dirs={'.git', '__pycache__', '.venv', '.vscode', 'node_modules', '.idea'}):
    for root, dirs, files in os.walk(startpath):
        # 原地过滤掉要忽略的文件夹
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = '    ' * level
        print(f'{indent}├── {os.path.basename(root)}/')
        
        sub_indent = '    ' * (level + 1)
        for f in files:
            # 忽略以 . 开头的隐藏文件（如 .gitignore 也可选择性过滤）
            if not f.startswith('.'):
                print(f'{sub_indent}├── {f}')

if __name__ == "__main__":
    # 使用当前目录（也可以用绝对路径）
    print_tree('.')
