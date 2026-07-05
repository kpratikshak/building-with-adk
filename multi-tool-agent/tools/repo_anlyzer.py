import os

def analyze_workspace(path: str = ".") -> str:
    """Scans the repository folder to understand the project structure and setup files.
    
    Args:
        path: The relative or absolute path to the repository root directory.
    """
    summary = []
    
    # 1. Map directory structure (skipping common noise like venv and git)
    summary.append("### Project Directory Structure:")
    ignored_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', 'dist', 'build'}
    
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 4 * level
        summary.append(f"{indent}- {os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            summary.append(f"{sub_indent}- {f}")
            
    # 2. Extract contents of configuration/dependency files if they exist
    summary.append("\n### Key Configuration Files:")
    manifest_files = ['pyproject.toml', 'package.json', 'requirements.txt', 'setup.py', 'go.mod']
    for manifest in manifest_files:
        manifest_path = os.path.join(path, manifest)
        if os.path.exists(manifest_path):
            summary.append(f"\n--- Content of {manifest} ---")
            with open(manifest_path, 'r', encoding='utf-8') as f:
                # Read first 50 lines to avoid blowing out token windows on huge requirement files
                summary.append("".join(f.readlines()[:50]))
                
    return "\n".join(summary)
