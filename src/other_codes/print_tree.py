import os

def print_tree(startpath, ignore_dirs={'.git', '__pycache__', '.venv', '.vscode', 'node_modules', '.idea'}):
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        level = root.replace(startpath, '').count(os.sep)
        indent = '    ' * level
        print(f'{indent}├── {os.path.basename(root)}/')
        sub_indent = '    ' * (level + 1)
        for f in files:
            if not f.startswith('.'):
                print(f'{sub_indent}├── {f}')

if __name__ == "__main__":
    # 默认打印当前目录的父目录（上一级）
    parent_dir = os.path.dirname(os.getcwd())   # 获取父目录路径
    print_tree(parent_dir)
