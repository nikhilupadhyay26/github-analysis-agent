import os
from dotenv import load_dotenv
from github import Github
import json
import textwrap
import openai

# Load environment variables from .env file
load_dotenv()

# Get API keys from the environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
openai.api_key = OPENAI_API_KEY

def main():
    username = "nikhilupadhyay26"
    repo_name = "todo-list"
    
    print(f"Fetching files from {username}/{repo_name} ...")
    files_info = fetch_repo_files(username, repo_name)
    
    if not files_info:
        print("No files found. Try a different repo or user with .py, .js, or .java files.")
        return
    
    # Let's skip README.md or any .md file
    first_non_md_file = None
    for file_info in files_info:
        # If the file does NOT end with '.md' (case-insensitive), pick it
        if not file_info["file_path"].lower().endswith(".md"):
            first_non_md_file = file_info
            break
    
    # If we didn't find any non-md file, there's nothing to analyze
    if not first_non_md_file:
        print("All files are Markdown (.md). No non-markdown files found to analyze.")
        return
    
    # Analyze the first non-md file
    file_path = first_non_md_file["file_path"]
    content = first_non_md_file["content"]
    
    print(f"Analyzing file: {file_path}")
    analysis_result = analyze_code(content)
    
    print("Analysis Result:")
    print(analysis_result)


# Helper functions
def list_user_repos(username):
    """Returns a list of public repository names for a given GitHub username."""
    # 1. Authenticate with GitHub using PyGithub
    g = Github(GITHUB_TOKEN)

    # 2. Get the user object
    user = g.get_user(username)

    # 3. Get repos
    repos = user.get_repos()

    # 4. Create a list of just the repo names
    repo_names = [repo.name for repo in repos]
    return repo_names

def fetch_repo_files(username, repo_name):
    """
    Returns a list of files for a given repo, with each file's path and content.
    """
    files_data = []
    
    # 1. Authenticate and get the repo object
    g = Github(GITHUB_TOKEN)
    user = g.get_user(username)
    repo = user.get_repo(repo_name)
    
    # 2. Start from the repo's root directory
    contents = repo.get_contents("")
    
    stack = contents if isinstance(contents, list) else [contents]
    
    while stack:
        file_item = stack.pop()
        
        if file_item.type == "dir":
            # If it's a directory, extend our stack with its contents
            sub_contents = repo.get_contents(file_item.path)
            stack.extend(sub_contents)
        else:
            # It's a file — let's get its content
            # (Be mindful of file size and type; you might only want .py, .js, etc.)
            file_path = file_item.path
            
            allowed_extensions = [".py", ".js", ".ts", ".java", ".md",".ipynb"]  # adjust as needed
            if any(file_path.endswith(ext) for ext in allowed_extensions):
                try:
                    content_str = file_item.decoded_content.decode("utf-8", errors="ignore")
                    files_data.append({
                        "file_path": file_path,
                        "content": content_str
                    })
                except Exception as e:
                    print(f"Error decoding file {file_path}: {e}")
    
    return files_data

def analyze_code(code_snippet):
    """
    Sends a code snippet to OpenAI and asks for code quality feedback.
    Returns a dict with parameter scores/comments or an error.
    """
    
    prompt = f"""
    You are a code reviewer. Please analyze the following code and provide feedback on:
    1) Readability (1-10)
    2) Maintainability (1-10)
    3) Documentation (1-10)
    Where 10 is the best score and 1 is the worst score. Be very critical and specific in giving the feedback and do not use
    generic terms. Give some actionable points to improve the code.

    Code:
    {textwrap.shorten(code_snippet, width=3500, placeholder="...")}

    Respond in JSON format only, like:
    {{
      "Readability": {{
        "score": 7,
        "comment": "Variable names are descriptive but formatting can improve."
      }},
      "Maintainability": {{
        "score": 6,
        "comment": "Code is modular, but more comments would help."
      }},
      "Documentation": {{
        "score": 5,
        "comment": "Docstrings are missing for most functions."
      }}
    }}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert code reviewer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        raw_output = response["choices"][0]["message"]["content"]
        
        # --- REMOVE MARKDOWN FENCES IF PRESENT ---
        cleaned_output = raw_output.strip()
        # If it starts with ``` and ends with ```
        # then remove the first and last line
        if cleaned_output.startswith("```") and cleaned_output.endswith("```"):
            lines = cleaned_output.splitlines()
            # Typically the first line is ```json (or just ```)
            # and the last line is ```
            # so we slice out everything in between
            cleaned_output = "\n".join(lines[1:-1]).strip()
        
        # OPTIONAL: If there's any extra triple backticks in the middle, remove them too:
        cleaned_output = cleaned_output.replace("```json", "").replace("```", "").strip()

        # Debug: Print what we're about to parse
        # print("CLEANED OUTPUT:\n", cleaned_output)

        data = json.loads(cleaned_output)
        return data

    except Exception as e:
        print("Error analyzing code:", e)
        return {
            "error": str(e),
            "raw_output": raw_output if 'raw_output' in locals() else ""
        }


if __name__ == "__main__":
    main()
