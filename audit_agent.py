import os
import subprocess
import json
import operator
import sys
import glob
import logging
from pathlib import Path
import shutil
from pypdf import PdfReader

from typing import TypedDict, Annotated, List, Optional, Dict, Any
from dotenv import load_dotenv

# LangGraph & LangChain
from langgraph.graph import StateGraph, END, START
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    try:
        from langgraph_checkpoint_sqlite import SqliteSaver
    except ImportError:
        # Fallback for older versions or missing sub-package
        SqliteSaver = None 

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI

# Visuals (Rich)
try:
    from playwright.sync_api import sync_playwright
    # Adaptive Stealth Import (v7.3.2)
    try:
        from playwright_stealth import stealth_sync
        def apply_stealth(page):
            stealth_sync(page)
    except ImportError:
        try:
            from playwright_stealth import Stealth
            def apply_stealth(page):
                s = Stealth()
                # Try multiple possible method names across versions
                if hasattr(s, 'apply_stealth_sync'):
                    s.apply_stealth_sync(page)
                elif hasattr(s, 'apply_stealth'):
                    s.apply_stealth(page)
                else:
                    # Fallback for some common wrapper patterns
                    from playwright_stealth import stealth_sync
                    stealth_sync(page)
        except:
            def apply_stealth(page):
                console.print("[yellow]⚠️ Warning: Stealth implementation failed, running without evasion.[/yellow]")
    PLAYWRIGHT_READY = True
except (ImportError, Exception) as e:
    PLAYWRIGHT_IMPORT_ERROR = str(e)
    PLAYWRIGHT_READY = False

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()
console = Console()

# ====================== Configuration ======================

class Config:
    # v6.4 Global Portability
    BASE_DIR = Path(__file__).resolve().parent
    
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    MODELS = {
        "gemini-flash": "gemini-2.5-flash",
        "gemini-pro": "gemini-3.1-pro-preview",
        "deepseek-r1": "deepseek-reasoner"
    }

    # v5.4.1 Restoration
    MYTHRIL_PATH = os.getenv("MYTHRIL_PATH", "mythril-env/bin/myth")
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

    # v5.2 Multi-Key Sniper: Support multiple keys for rotation
    RAW_KEYS = os.getenv("GOOGLE_API_KEYS", os.getenv("GOOGLE_API_KEY", ""))
    GOOGLE_API_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip()]
    
    # Optimized routing for Free Tier Quota (v4.7)

    MODEL_ROUTING = {
        "fast_analyzer": "gemini-flash",
        "triage": "gemini-flash",
        "deep_auditor": "deepseek-r1",
        "invariant_miner": "deepseek-r1", # v6.0 Deep Reasoning
        "fuzz_engineer": "gemini-flash",
        "poc_generator": "gemini-flash", 
        "report_writer": "gemini-flash",
        "reviewer": "gemini-flash"
    }

    # v6.0 Universal Hunter Tools
    NUCLEI_PATH = os.getenv("NUCLEI_PATH", "nuclei")

    HTTPX_PATH = os.getenv("HTTPX_PATH", "httpx")
    APKTOOL_PATH = os.getenv("APKTOOL_PATH", "apktool")
    APKLEAKS_PATH = os.getenv("APKLEAKS_PATH", "apkleaks")

    TIMEOUTS = {
        "aderyn": 180,
        "slither": 120,
        "mythril": 300,
        "surya": 60,
        "forge": 180,
        "nuclei": 600,
        "apkleaks": 300
    }
    
    MAX_RETRIES = 1 # v7.2.1 Emergency Quota Protection
    FUZZ_RUNS = 1000
    
    # v8.0 Professional Hunter Layer
    RPC_URL = os.getenv("RPC_URL", "")
    FORK_BLOCK_NUMBER = os.getenv("FORK_BLOCK_NUMBER", "")
    
    # v10.1 Stealth & Rate Limiting
    MAX_RPS = 5
    PROXY_LIST = [] # Restore Proactive proxy support

    
    # v10.0 Co-Pilot UI
    DASHBOARD = None
    CURRENT_PHASE = "Standing by..."
    TARGET_CONFIDENCE = 0
    FOUND_VULNS_COUNT = 0
    
    # v10.2 Interactive Auth Layer
    SHOW_BROWSER = os.getenv("SHOW_BROWSER", "False").lower() == "true"
    COOKIES_FILE = Path("arsenal_cookies.json")

    # v13.0 Expansion: Specialist Web2 Tools
    # Go-based (Global Path)
    FFUF_PATH = "ffuf"
    DALFOX_PATH = "dalfox"
    INTERACTSH_PATH = "interactsh-client" 

    # Python-based (Local Path in /tools)
    PYTHON_VENV_EXE = BASE_DIR / "tools/venv/bin/python"
    SQLMAP_EXE = BASE_DIR / "tools/sqlmap/sqlmap.py"
    ARJUN_EXE = BASE_DIR / "tools/Arjun/arjun.py"
    LINKFINDER_EXE = BASE_DIR / "tools/LinkFinder/linkfinder.py"
    SECRETFINDER_EXE = BASE_DIR / "tools/SecretFinder/SecretFinder.py"
    COMMIX_EXE = BASE_DIR / "tools/commix/commix.py"
    TPLMAP_EXE = BASE_DIR / "tools/tplmap/tplmap.py"

# ====================== Co-Pilot UI (Rich Live) ======================

class LiveDashboard:
    def __init__(self):
        self.live = Live(self.generate_table(), refresh_per_second=4, transient=True)
        
    def generate_table(self, thought: str = "") -> Table:
        table = Table(title="🛡️ ARSENAL V14.2 [bold magenta]STRATEGIC CO-PILOT[/bold magenta]", border_style="bold blue", expand=True)
        table.add_column("Phase & Target", justify="left", style="cyan", ratio=1)
        table.add_column("AI Thought Stream", justify="left", style="italic magenta", ratio=2)
        table.add_column("Stats", justify="right", style="yellow", ratio=1)
        
        # Format the thought to look like a conscious stream
        thought_display = f"🧠 [italic]{thought or 'Waiting for next strategic move...'}[/italic]"
        
        stats = f"🔥 Findings: [bold red]{Config.FOUND_VULNS_COUNT}[/bold red]\n🎯 Confidence: {Config.TARGET_CONFIDENCE}%"
        
        table.add_row(
            f"{Config.CURRENT_PHASE}\n[dim]Target: {os.getenv('TARGET_URL', 'Idle')}[/dim]",
            thought_display,
            stats
        )
        return table
        
    def update(self, thought: str = ""):
        self.live.update(self.generate_table(thought))


    def start(self):
        self.live.start()
        
    def stop(self):
        self.live.stop()

Config.DASHBOARD = LiveDashboard()



import threading
class SessionRegistry:
    """v12.0 Thread-local session tracking to prevent API key collisions in parallel audits."""
    _storage = threading.local()

    @classmethod
    def _ensure_init(cls):
        if not hasattr(cls._storage, "data"):
            cls._storage.data = {
                "current_key_idx": 0,
                "failed_keys": set(),
                "last_req_time": 0
            }

    @classmethod
    def get_idx(cls):
        cls._ensure_init()
        return cls._storage.data["current_key_idx"]

    @classmethod
    def set_idx(cls, idx):
        cls._ensure_init()
        cls._storage.data["current_key_idx"] = idx

    @classmethod
    def get_failed(cls):
        cls._ensure_init()
        return cls._storage.data["failed_keys"]

    @classmethod
    def get_last_req(cls):
        cls._ensure_init()
        return cls._storage.data["last_req_time"]

    @classmethod
    def set_last_req(cls, t):
        cls._ensure_init()
        cls._storage.data["last_req_time"] = t

_model_cache = {}

def get_model(role: str):
    """v11.0 Cache-aware Model Factory. Reuse instances to save RAM."""
    global _model_cache
    model_key = Config.MODEL_ROUTING.get(role, "gemini-flash")
    
    if not Config.GOOGLE_API_KEYS:
        raise ValueError("No GOOGLE_API_KEY or GOOGLE_API_KEYS found in .env!")
    
    # v12.0 Session-local indexing
    current_idx = SessionRegistry.get_idx()
    current_key = Config.GOOGLE_API_KEYS[current_idx % len(Config.GOOGLE_API_KEYS)]
    model_name = Config.MODELS.get(model_key, Config.MODELS["gemini-flash"])
    
    cache_key = (model_name, current_key)
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    if model_key == "deepseek-r1":
        model = ChatDeepSeek(
            model=Config.MODELS["deepseek-r1"],
            api_key=Config.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            temperature=0.2
        )
    else:
        model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=current_key,
            temperature=0.1,
            max_retries=0
        )
    
    _model_cache[cache_key] = model
    return model

def rotate_key():
    """Trigger rotation to the next available API key in current session."""
    current_idx = SessionRegistry.get_idx()
    failed_keys = SessionRegistry.get_failed()
    
    new_idx = current_idx + 1
    start_idx = new_idx % len(Config.GOOGLE_API_KEYS)
    check_idx = start_idx
    
    while Config.GOOGLE_API_KEYS[check_idx] in failed_keys:
        new_idx += 1
        check_idx = new_idx % len(Config.GOOGLE_API_KEYS)
        if check_idx == start_idx: break
        
    SessionRegistry.set_idx(new_idx)
    console.print(f"[bold yellow]🔄 Session Rotation: Instantly rotating to Key #{check_idx + 1}...[/bold yellow]")

def enforce_rate_limit():
    """Ensure we don't exceed MAX_RPS with session-local tracking."""
    import time
    import random
    
    current_time = time.time()
    last_req = SessionRegistry.get_last_req()
    elapsed = current_time - last_req
    min_interval = 1.0 / Config.MAX_RPS
    
    if elapsed < min_interval:
        sleep_time = (min_interval - elapsed) + random.uniform(0.05, 0.15)
        time.sleep(sleep_time)
        
    SessionRegistry.set_last_req(time.time())

def invoke_with_retry(role: str, messages: list, max_rotations: int = None):
    """v5.3 Sniper: Invoke model and rotate INSTANTLY on 429 errors."""
    enforce_rate_limit()
    if max_rotations is None:
        max_rotations = len(Config.GOOGLE_API_KEYS)
    
    attempt = 0
    while attempt <= max_rotations:
        try:
            model = get_model(role)
            return model.invoke(messages)
        except Exception as e:
            err_msg = str(e).upper()
            if any(x in err_msg for x in ["429", "RESOURCE_EXHAUSTED", "QUOTA"]):
                current_idx = SessionRegistry.get_idx()
                current_key = Config.GOOGLE_API_KEYS[current_idx % len(Config.GOOGLE_API_KEYS)]
                SessionRegistry.get_failed().add(current_key)
                
                if attempt < max_rotations:
                    rotate_key()
                    attempt += 1
                    continue
                else: 
                     console.print("[bold red]❌ ALL API KEYS EXHAUSTED FOR TODAY. Stopping.[/bold red]")
                     raise e
            else:
                raise e


# ====================== State Definition ======================

class AgentState(TypedDict):
    repo_url: str
    code_path: Path
    project_root: Path
    source_dir: str
    project_structure: str
    intent_summary: str
    in_scope_patterns: List[str]
    security_knowledge: str
    aderyn_output: str
    mythril_output: str
    surya_output: str
    target_vulns: List[Dict[str, Any]]
    current_index: int
    retry_count: int
    logs: str
    current_context: List[str]
    poc_code: str
    verification_result: str
    reports: List[str]
    final_report: str
    
    # v10.4 Refined Audit Fields
    business_logic: str          # From Protocol Architect
    intent_summary: str          # From Intent node
    core_code_context: str       # From Ingestor
    project_invariants: str      # Technical Invariants
    invariant_test_code: str     # Fuzz test code
    fuzz_logs: str               # Fuzz results

    
    # v6.0 Universal Fields
    target_type: str             # "web3", "web2", "mobile", "api"
    recon_data: Dict[str, Any]
    scan_reports: List[str]
    web_findings: List[Dict[str, Any]]
    mobile_findings: List[Dict[str, Any]]
    
    # v6.1 Interactive Pentester Fields
    dom_snapshot: str
    browser_logs: List[str]
    captured_requests: List[Dict[str, Any]]
    
    # v6.2 Resilient Hunter Fields
    audit_status: str            # "COMPLETE", "PARTIAL", "FAILED"
    coverage_score: float        # 0.0 to 1.0 (actions completed / total)
    
    messages: Annotated[List[BaseMessage], operator.add]
    
    # v10.4 Refined Routing & Strategy
    last_node: str               # To replace volatile Config.CURRENT_PHASE for routing
    strategy: str                # Strategy generated by Commander

    # v13.0 Expansion Data
    js_endpoints: List[str]      # From LinkFinder
    js_secrets: List[str]        # From SecretFinder
    discovered_params: Dict[str, List[str]] # From Arjun
    fuzz_results: List[str]      # From ffuf
    
    # v14.2 "Conscious Pentester" Data
    current_thought: str         # Natural language reasoning stream




# ====================== Utilities ======================

def safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    """Robustly extract and parse JSON from LLM response strings."""
    try:
        # 1. Try direct parse
        return json.loads(text.strip())
    except json.JSONDecodeError:
        try:
            # 2. Try cleaning markdown blocks
            if "```json" in text:
                content = text.split("```json")[-1].split("```")[0].strip()
                return json.loads(content)
            elif "```" in text:
                content = text.split("```")[-1].split("```")[0].strip()
                return json.loads(content)
            
            # 3. Last ditch: Regex-based extraction for robustness
            import re
            match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            pass
            
    return None


def run_cmd(args: List[str], cwd: Optional[Path] = None, timeout: int = 60) -> tuple[bool, str]:
    """Helper to run shell commands safely and capture output."""
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Command timed out."
    except Exception as e:
        return False, str(e)

def run_cmd_with_retry(args: List[str], cwd: Path, timeout: int = 60, tries: int = 2) -> tuple[bool, str]:
    """v12.0 Resilient shell executor with exponential fallback."""
    import time
    last_err = ""
    for i in range(tries):
        success, output = run_cmd(args, cwd, timeout)
        if success: return True, output
        last_err = output
        if i < tries - 1:
            time.sleep(5 * (i + 1))
    return False, last_err


# v7.2 Persistence Layer
import sqlite3
class HistoryDB:
    def __init__(self, db_path="arsenal_memory.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS attack_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_url TEXT,
                selector TEXT,
                payload TEXT,
                result_code INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except:
                pass



    def record_attack(self, url, selector, payload, code):
        self.cursor.execute("INSERT INTO attack_history (target_url, selector, payload, result_code) VALUES (?, ?, ?, ?)",
                            (url, selector, payload, code))
        self.conn.commit()

    def was_tried(self, url, selector, payload):
        self.cursor.execute("SELECT 1 FROM attack_history WHERE target_url=? AND selector=? AND payload=?", (url, selector, payload))
        return self.cursor.fetchone() is not None

def check_tool(name: str) -> bool:
    """v11.0 Robust tool check using shutil.which and fallback --version."""
    if shutil.which(name):
        return True
        
    # Special cases for named tools
    if name == "mythril":
        return shutil.which("myth") is not None
        
    try:
        # Fallback to --version check
        subprocess.run([name, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False


# ====================== Browser Tools (v6.1) ======================

class BrowserScout:
    def __init__(self):
        """Initialize browser with v7.5 Single-Launch logic with Proxy/Stealth."""
        if not PLAYWRIGHT_READY:
            raise ImportError(f"Playwright/Stealth not ready: {PLAYWRIGHT_IMPORT_ERROR}")
            
        self.pw = sync_playwright().start()
        
        # v7.5 Single-Launch logic with Proxy/Stealth
        browser_args = ["--disable-blink-features=AutomationControlled"]
        proxy_config = None
        if Config.PROXY_LIST:
            import random
            p_url = random.choice(Config.PROXY_LIST).strip()
            if p_url:
                proxy_config = {"server": p_url}
                console.print(f"[bold blue]🌐 Proxy Rotation: Using {p_url}[/bold blue]")

        # v10.2 Headful Mode for Manual Login
        self.browser = self.pw.chromium.launch(
            headless=not Config.SHOW_BROWSER, 
            args=browser_args,
            proxy=proxy_config,
            # Increasing explicit timeout for headful scenarios
            timeout=60000 if Config.SHOW_BROWSER else 30000
        )
        
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        
        # v10.2 Load Previous Session Cookies
        if Config.COOKIES_FILE.exists():
            try:
                with open(Config.COOKIES_FILE, "r") as f:
                    cookies = json.load(f)
                self.context.add_cookies(cookies)
                console.print(f"[bold green]🍪 Loaded {len(cookies)} saved cookies into browser session.[/bold green]")
            except Exception as e:
                console.print(f"[red]⚠️ Failed to load cookies: {e}[/red]")
        
        # v7.1 Console Monitor
        self.console_logs = []
        self.page.on("console", lambda msg: self.console_logs.append(f"[{msg.type}] {msg.text}"))
        
        # v7.3.2 Adaptive Stealth
        apply_stealth(self.page)
        
        self.captured_requests = []
        self.page.on("request", lambda request: self.captured_requests.append({
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers)
        }))

    def save_session_cookies(self):
        """v10.2 Dump current session cookies to file."""
        try:
            cookies = self.context.cookies()
            with open(Config.COOKIES_FILE, "w") as f:
                json.dump(cookies, f, indent=2)
            console.print(f"[bold green]🍪 Saved {len(cookies)} cookies to disk.[/bold green]")
        except Exception as e:
            console.print(f"[red]⚠️ Failed to save cookies: {e}[/red]")

    def navigate(self, url: str):
        # v6.2 Human-like delay
        import random
        import time
        time.sleep(random.uniform(1.0, 3.0))
        self.page.goto(url, wait_until="networkidle")

    def get_snapshot(self):
        """v7.2 - Accessibility Tree Snapshot (Cleaner for AI)."""
        try:
            return self.page.accessibility.snapshot()
        except:
            return self.page.content()[:30000]

    def perform_action(self, action_data: Dict[str, Any]):
        """Execute click/type/navigate based on LLM decision."""
        try:
            a_type = action_data.get("type")
            selector = action_data.get("selector")
            value = action_data.get("value")
            
            # v10.1 Rate Limiting (re-applied here for safety)
            enforce_rate_limit()

            if a_type == "click":
                self.page.click(selector, timeout=5000)
            elif a_type == "type":
                self.page.fill(selector, value, timeout=5000)
            elif a_type == "navigate":
                self.page.goto(value, wait_until="networkidle")
            
            # v12.0 Browser Rate Limiting (Anti-detection & Safety)
            import time
            time.sleep(1.0)
            
            self.page.wait_for_timeout(1000)
            return True, f"Executed {a_type} on {selector or value}"

        except Exception as e:
            return False, str(e)

    def is_alive(self):
        """v7.5 Check if browser is still connected."""
        return self.browser and self.browser.is_connected()

    def close(self):
        self.browser.close()
        self.pw.stop()

# ====================== Graph Nodes ======================

def environment_check_node(state: AgentState):
    """v11.0 - Expanded Proactive Environment Check & Auto-Discovery."""
    console.print("[bold yellow]🔍 Checking Security Arsenal Integrity (V11.0 Hardening)...[/bold yellow]")
    
    # Comprehensive tool mapping (Web3 + Web2 + Mobile)
    tools_to_check = {
        "nmap": "Exploration",
        Config.NUCLEI_PATH: "Web Scan",
        "slither": "Static Analysis (Web3)",
        "aderyn": "Static Analysis (Web3)",
        "mythril": "Symbolic Execution (Web3)",
        "surya": "Call Graph (Web3)",
        "forge": "Fuzzing/PoC (Web3)",
        "subfinder": "Recon (Wildcard)",
        "httpx": "Recon (Wildcard)",
        # v13.0 Go Tools (Global)
        Config.FFUF_PATH: "Directory Fuzzing",
        Config.DALFOX_PATH: "XSS Analysis",
        Config.INTERACTSH_PATH: "OOB Testing"
    }
    
    missing = []
    for tool, category in tools_to_check.items():
        if not check_tool(tool):
            # Special case for tool paths in Config
            if tool == Config.NUCLEI_PATH:
                # Try discovery
                success, path = run_cmd(["which", "nuclei"])
                if success: 
                    Config.NUCLEI_PATH = path.strip()
                    continue
            missing.append(f"{tool} ({category})")
    
    # 2. Check Python Specialist Tools (v13.0)
    py_tools = {
        "Arjun": Config.ARJUN_EXE,
        "LinkFinder": Config.LINKFINDER_EXE,
        "SecretFinder": Config.SECRETFINDER_EXE,
        "sqlmap": Config.SQLMAP_EXE,
        "commix": Config.COMMIX_EXE,
        "tplmap": Config.TPLMAP_EXE
    }
    for name, path in py_tools.items():
        if not path.exists():
            missing.append(f"{name} (Python tool missing at {path})")


    # 3. Check Playwright
    if not PLAYWRIGHT_READY:
        console.print(f"[bold red]❌ Playwright Impact Pack missing or broken:[/bold red] {globals().get('PLAYWRIGHT_IMPORT_ERROR', 'Unknown Error')}")
        missing.append("Playwright (Python)")
    else:
        # Lightweight check: Just verify chromium exists in the playwright package, don't launch a full browser
        try:
             from playwright.sync_api import sync_playwright
        except:
             missing.append("Playwright (Browsers)")



    if missing:
        msg = f"MISSING TOOLS: {', '.join(missing)}"
        t_type = state.get("target_type", "")
        # Critical failure only if core tools for that path are missing
        if t_type == "web2" and ("Playwright" in msg or "Nuclei" in msg or "ffuf" in msg):
             console.print(f"[bold red]❌ Environment Check FAILED for Web2: {msg}[/bold red]")
             return {"audit_status": f"FAILED ({msg})", "coverage_score": 0.0}
        else:
             console.print(f"[bold yellow]⚠️ Environment Check PARTIAL: Some tools missing ({msg}) but proceeding.[/bold yellow]")
    
    console.print("[bold green]✅ Security Arsenal READY (V13.0 Expanded)[/bold green]")
    return {"audit_status": "READY", "coverage_score": 1.0}


def triage_target_node(state: AgentState):
    """Categorize the target and route the workflow."""
    target = state["repo_url"]

    console.print(f"[bold cyan]🎯 Triaging Target: {target}[/bold cyan]")
    
    # Determine target type (v9.0 Wildcard Support)
    if target.endswith(".apk") or target.endswith(".ipa"):
        t_type = "mobile"
    elif target.startswith("http") or target.startswith("*"):
        t_type = "wildcard" if "*" in target else "web2"
    else:
        t_type = "web3"

    # v10.3 Guarantee code_path is a valid Path object to avoid NoneType errors
    code_path = Path("temp_repo") if t_type == "web3" else Path("./")
        
    return {
        "target_type": t_type, 
        "repo_url": target, 
        "code_path": code_path, 
        "project_root": code_path,
        "reports": []
    }

def wildcard_recon_node(state: AgentState):
    """v9.0 - Wildcard Recon Crawler using subfinder and httpx."""
    console.print(f"[bold cyan]🔍 WILDCARD RECON: Scanning {state['repo_url']}...[/bold cyan]")
    
    target = state["repo_url"]
    # Sanitize domain to prevent command injection
    import re
    domain = target.replace("https://", "").replace("http://", "").replace("*.", "").replace("*", "")
    domain = re.sub(r'[^a-zA-Z0-9.-]', '', domain)
    
    cmd = f"subfinder -d {domain} -silent | httpx -silent -mc 200,302"
    console.print(f"[dim]Running: {cmd}[/dim]")
    
    try:
        # v10.4 Security: Refactored to avoid shell=True by using manual pipes.
        # Equivalent to: subfinder -d {domain} -silent | httpx -silent -mc 200,302
        p1 = subprocess.Popen(["subfinder", "-d", domain, "-silent"], stdout=subprocess.PIPE, text=True)
        p2 = subprocess.run(["httpx", "-silent", "-mc", "200,302"], stdin=p1.stdout, capture_output=True, text=True, timeout=300)
        p1.stdout.close() # Allow p1 to receive a SIGPIPE if p2 exits.
        
        live_subdomains = p2.stdout.strip().split('\n')
        live_subdomains = [d.strip() for d in live_subdomains if d.strip()]
    except Exception as e:
        live_subdomains = []
        console.print(f"[red]Wildcard Recon failed: {e}[/red]")

        
    if not live_subdomains:
        console.print("[yellow]⚠️ No live subdomains found or tools missing. Falling back to base domain.[/yellow]")
        return {"repo_url": f"https://{domain}", "recon_data": state.get("recon_data", {})}
        
    console.print(f"[bold green]✅ Found {len(live_subdomains)} live targets. Triaging...[/bold green]")
    
    prompt = f"""You are a Bug Bounty Triage Expert.
We discovered {len(live_subdomains)} live subdomains for {domain}.
List of subdomains:
{chr(10).join(live_subdomains[:100])}

Identify the SINGLE MOST CRITICAL AND VULNERABLE target from this list (focus on dev, staging, api, admin, test).
Return ONLY the full URL starting with http/https. No markdown, no explanations."""

    model_role = "deep_auditor"
    response = invoke_with_retry(model_role, [HumanMessage(content=prompt)])
    best_target = response.content.strip()
    
    import re
    urls = re.findall(r'(https?://[^\s]+)', best_target)
    if urls: best_target = urls[0]
    else: best_target = f"https://{domain}"
    
    recon = state.get("recon_data", {})
    recon["live_subdomains"] = live_subdomains
    
    console.print(f"[bold purple]🎯 AI Target Selected: {best_target}[/bold purple]")
    
    return {"repo_url": best_target, "recon_data": recon, "last_node": "wildcard_recon"}


def web_recon_node(state: AgentState):
    """Perform initial reconnaissance on a web target."""
    target = state["repo_url"]
    thought = f"🔭 Initiating deep reconnaissance on {target}. Identifying attack surface and mapping subdomains..."
    console.print(f"[bold magenta]🌐 {thought}[/bold magenta]")
    
    # 1. Nmap scan for open ports
    domain = target.replace("https://", "").replace("http://", "").split("/")[0]
    success, output = run_cmd(["nmap", "-F", domain], timeout=120)
    
    # 2. Extract endpoints if possible (Mock/Simple)
    recon_data = {
        "domain": domain,
        "nmap_output": output if success else "Nmap failed",
        "endpoints": []
    }
    
    return {"recon_data": recon_data, "current_thought": thought}


def auth_gate_node(state: AgentState):
    """v10.2 Interactive Auth Gate. Pauses if login is required."""
    target = state["repo_url"]
    
    # Simple heuristic to detect if auth might be needed.
    needs_auth = "login" in target.lower() or "signin" in target.lower() or "auth" in target.lower()
    
    # Or force it if user configured it
    force_auth = os.getenv("AUTH_CHECK_REQUIRED", "False").lower() == "true"
    
    if needs_auth or force_auth:
        console.print(f"[bold magenta]🔐 AUTH GATE: Login may be required for {target}[/bold magenta]")
        
        if Config.SHOW_BROWSER:
            console.print("[bold yellow]Browser is visible. Please perform login manually now.[/bold yellow]")
            user_input = input(">>> Press ENTER when you have successfully logged in (or type 'skip')... ").strip()
            
            if user_input.lower() != 'skip':
                # The browser should be instantiated in Interactive Scout, but since Auth Gate
                # needs it, we instantiate a temporary one to grab cookies if needed.
                # In this architecture, it's better to tell Scout to save cookies.
                console.print("[bold green]✅ Auth confirmed. Proceeding with scan...[/bold green]")
        else:
            console.print("[yellow]⚠️ Warning: Possible login page detected, but SHOW_BROWSER=False in .env.[/yellow]")
            console.print("[yellow]The agent will proceed but might fail if authentication is strictly enforced.[/yellow]")
            
    return {}

def web_scan_node(state: AgentState):
    """Run automated vulnerability scanners (Nuclei)."""
    target = state["repo_url"]
    thought = f"🛡️ Launching Nuclei CVE scan engine. Looking for known vulnerabilities and configuration leaks on {target}..."
    console.print(f"[bold red]🔍 {thought}[/bold red]")
    
    # Execute Nuclei
    success, output = run_cmd([Config.NUCLEI_PATH, "-u", target, "-silent"], timeout=Config.TIMEOUTS["nuclei"])

    
    findings = []
    if success:
        for line in output.splitlines():
            if line.strip():
                findings.append({"type": "Nuclei Finding", "description": line.strip(), "confidence": "High"})
    
    return {"scan_reports": [output], "web_findings": findings, "target_vulns": findings}


def fuzzer_node(state: AgentState):
    """Run ffuf for path and directory discovery."""
    target = state["repo_url"]
    console.print(f"[bold red]🚀 Fuzzing targets with ffuf on {target}...[/bold red]")
    
    # Using a common wordlist fallback (standard on most Linux distros)
    wordlist = "/usr/share/wordlists/dirb/common.txt"
    if not Path(wordlist).exists():
        # Fallback to a tiny internal list if no system wordlist
        wordlist = "common_paths.txt"
        if not Path(wordlist).exists():
             Path(wordlist).write_text(".env\n.git\nadmin\nconfig\nbackup\napi\nv1\nv2\nwp-admin\nphpmyadmin\n.htaccess\n.ssh")
             
    fuzz_url = f"{target.rstrip('/')}/FUZZ"
    success, output = run_cmd([Config.FFUF_PATH, "-u", fuzz_url, "-w", wordlist, "-mc", "200,301,302", "-silent"], timeout=300)
    
    results = []
    if success:
        for line in output.splitlines():
            if line.strip(): results.append(line.strip())
            
    return {"fuzz_results": results}

def js_analyst_node(state: AgentState):
    """Extract endpoints and secrets from JavaScript files discovered during recon."""
    target = state["repo_url"]
    console.print(f"[bold yellow]📜 JS Analyst: Extracting intelligence from JavaScript...[/bold yellow]")
    
    # 1. Identify JS files from recon_data
    js_urls = []
    # Mix of subdomains found and live urls from httpx
    recon_urls = state.get("recon_data", {}).get("live_urls", [])
    for url in recon_urls:
        if url.endswith(".js"):
            js_urls.append(url)
            
    # Also check the main target
    if target.endswith(".js"): js_urls.append(target)
    
    found_endpoints = []
    found_secrets = []
    
    # Limit to top 5 JS files to save time/tokens
    for js_url in js_urls[:5]:
        console.print(f"   [dim]Analyzing {js_url}...[/dim]")
        # 1. LinkFinder
        lf_cmd = [str(Config.PYTHON_VENV_EXE), str(Config.LINKFINDER_EXE), "-i", js_url, "-o", "cli"]
        s1, out1 = run_cmd(lf_cmd, timeout=60)
        if s1: found_endpoints.extend(out1.splitlines())
        
        # 2. SecretFinder
        sf_cmd = [str(Config.PYTHON_VENV_EXE), str(Config.SECRETFINDER_EXE), "-i", js_url, "-o", "cli"]
        s2, out2 = run_cmd(sf_cmd, timeout=60)
        if s2: found_secrets.extend(out2.splitlines())

    return {"js_endpoints": list(set(found_endpoints)), "js_secrets": list(set(found_secrets))}

def param_miner_node(state: AgentState):
    """Discover hidden parameters using Arjun."""
    target = state["repo_url"]
    console.print(f"[bold magenta]💎 Param Miner: Discovering hidden parameters on {target}...[/bold magenta]")
    
    cmd = [str(Config.PYTHON_VENV_EXE), str(Config.ARJUN_EXE), "-u", target, "--stable"]
    success, output = run_cmd(cmd, timeout=180)
    
    params = {}
    if success:
         # Arjun output is usually verbose, we try to extract found params
         import re
         matches = re.findall(r'Parameters found: (.*)', output)
         if matches:
              params[target] = matches[0].split(", ")
              
    return {"discovered_params": params}

def injection_expert_node(state: AgentState):
    """Launch specialized injection tools based on findings."""
    target = state["repo_url"]
    web_findings = state.get("web_findings", [])
    
    # 1. Decide which tool to run based on findings or target profile
    findings_str = "\n".join([f["description"] for f in web_findings])
    
    injection_results = []
    
    # SQLmap if suspicious
    if "sql" in findings_str.lower() or "?" in target:
        console.print("[bold red]💉 Injection Expert: Launching sqlmap...[/bold red]")
        cmd = [str(Config.PYTHON_VENV_EXE), str(Config.SQLMAP_EXE), "-u", target, "--batch", "--level=1", "--risk=1"]
        s, out = run_cmd(cmd, timeout=300)
        if "is vulnerable" in out: injection_results.append(f"SQLMAP: {out[:1000]}")

    # Commix if OS cmd injection suspected
    if "rce" in findings_str.lower() or "cmd" in findings_str.lower():
        console.print("[bold red]💉 Injection Expert: Launching commix...[/bold red]")
        cmd = [str(Config.PYTHON_VENV_EXE), str(Config.COMMIX_EXE), "--url", target, "--batch"]
        s, out = run_cmd(cmd, timeout=180)
        if "is vulnerable" in out: injection_results.append(f"COMMIX: {out[:1000]}")

    # Dalfox for XSS
    console.print("[bold red]💉 Injection Expert: Launching Dalfox (XSS)...[/bold red]")
    cmd = [Config.DALFOX_PATH, "url", target, "--silent"]
    s, out = run_cmd(cmd, timeout=180)
    if out.strip(): injection_results.append(f"DALFOX: {out[:1000]}")

    return {"scan_reports": state.get("scan_reports", []) + injection_results, "current_thought": "Finished deep injection analysis. Passing findings to Commander for final strategy."}

def logic_architect_node(state: AgentState):
    """v14.2 Specialized node for Business Logic Vulnerability Analysis."""
    target = state["repo_url"]
    thought = f"🧠 Analyizing business logic flows for {target}. Mapping sensitive state transitions (Auth, CRUD, Payment)..."
    console.print(f"[bold blue]💎 {thought}[/bold blue]")
    
    # Reasoning logic: What are the high-risk logic points here?
    prompt = f"""You are a SENIOR LOGIC PENTESTER.
Analyze the target: {target}
Known Endpoints: {state.get('recon_data', {}).get('live_subdomains', [])}
Detected Params: {state.get('discovered_params', {})}

Think like an attacker:
1. Identify 3 critical business flows (e.g., signup -> verify, cart -> checkout).
2. Suggest 2 logic-specific attacks (IDOR, Privilege Escalation, Price Manipulation) to try next.
3. Generate a Playwright execution plan to test these flows.

Format: Provide a structured 'Logic Assessment'."""

    model_role = "deep_auditor"
    # Capture reasoning if using DeepSeek R1
    response = invoke_with_retry(model_role, [HumanMessage(content=prompt)])
    logic_assessment = response.content
    
    # v14.2 Extraction of natural language reasoning for the Thought Stream
    # If the response contains <thought> tags (standard R1), we'll extract them
    import re
    thoughts = re.findall(r'<thought>(.*?)</thought>', logic_assessment, re.DOTALL)
    if thoughts:
        short_thought = f"Logic Research: {thoughts[0][:300]}..."
    else:
        short_thought = f"Identifying logic flows for {target} targets..."

    return {
        "business_logic": logic_assessment,
        "current_thought": short_thought,
        "scan_reports": state.get("scan_reports", []) + [f"LOGIC ASSESSMENT:\n{logic_assessment}"]
    }



def mobile_static_node(state: AgentState):
    """Perform static analysis on a mobile app package."""
    target_path = state["code_path"]
    console.print(f"[bold yellow]📱 Static Analysis on Mobile App...[/bold yellow]")
    
    # 1. Run APKLeaks if target is an APK
    findings = []
    if str(target_path).endswith(".apk"):
        success, output = run_cmd([Config.APKLEAKS_PATH, "-f", str(target_path)], timeout=Config.TIMEOUTS["apkleaks"])
        if success:
            findings.append({"type": "Mobile Leaks", "description": output[:2000], "confidence": "High"})
            
    return {"mobile_findings": findings, "target_vulns": findings}

def librarian_rag_node(state: AgentState):
    """v7.4 - Intelligent Librarian (RAG). Filters 30k+ tokens into relevant snippets."""
    console.print("[bold yellow]📚 LIBRARIAN is retrieving relevant intelligence...[/bold yellow]")
    
    # v12.0 Intelligence Fallback
    intelligence_path = Path("Arsenal_Intelligence.md")
    if not intelligence_path.exists():
        console.print("[yellow]⚠️ Warning: Arsenal_Intelligence.md not found. Librarian RAG will have no context.[/yellow]")
        return {"scan_reports": state.get("scan_reports", []) + ["Knowledge base missing."]}

    
    selected_intel = []
    if intelligence_path.exists():
        with open(intelligence_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Split into sections (assuming markdown headers)
            sections = content.split("##")
            for section in sections:
                if any(kw in section.lower() for kw in query_keywords):
                    selected_intel.append(section[:2000]) # Keep top 2k per section
                    
    # Return top relevant blocks to save context
    recon = state.get("recon_data", {})
    recon["relevant_intel"] = selected_intel[:3]
    return {"recon_data": recon}


def commander_node(state: AgentState):
    """v7.4 - The Mastermind (DeepSeek R1). Generates Strategy + Mermaid Chart."""
    console.print("[bold purple]🏰 COMMANDER (DeepSeek R1) is strategizing...[/bold purple]")
    
    recon = state.get("recon_data", {})
    dom = state.get("dom_snapshot", "")
    intel = recon.get("relevant_intel", "N/A")
    
    prompt = f"""You are a CHIEF SECURITY ARCHITECT.
Target: {state['repo_url']}
Filtered Intelligence: {intel}
Accessibility Tree: {dom}

Task:
1. Establish a Strategic Attack Tree.
2. Generate a Mermaid Diagram code block for this strategy.

Output a Strategic Attack Tree in JSON format:
{{
  "objectives": [...],
  "mermaid_chart": "graph TD\nA[Start] --> B[Target Login]...",
  "reasoning": "..."
}}"""

    model_role = "deep_auditor"
    response = invoke_with_retry(model_role, [HumanMessage(content=prompt)])
    data = safe_json_parse(response.content)
    
    # v7.4 Visualization Export
    if data and "mermaid_chart" in data:
        with open("attack_strategy.md", "w", encoding="utf-8") as f:
            f.write("# 🏰 Arsenal Strategic Attack Tree\n\n```mermaid\n")
            f.write(data["mermaid_chart"])
            f.write("\n```\n\n## Reasoning\n" + data.get("reasoning", ""))
            
    return {"strategy": response.content, "last_node": "commander"}


def interactive_scout_node(state: AgentState):
    """The 'Eyes and Hands' of the AI: Interacts with the web page (v7.2 Mastery)."""
    if not PLAYWRIGHT_READY:
        console.print("[yellow]⚠️ Playwright not installed. Skipping interactive test.[/yellow]")
        return {"audit_status": "PARTIAL", "coverage_score": 0.0}

    target = state["repo_url"]
    strategy = state.get("strategy", "No specific strategy.")
    
    console.print(f"[bold cyan]🕵️ Mastermind Scout is entering {target}...[/bold cyan]")
    
    try:
        with HistoryDB() as db:
            scout = BrowserScout()
            scout.navigate(target)
            
            # Iterative Exploration & Attack Loop (v7.2 Persistence & Strategy)
            total_intended = 5
            success_count = 0
            
            for i in range(total_intended):
                dom = scout.get_snapshot()
                
                # Using Professional Research terminology (v7.5)
                prompt = f"""You are a SENIOR SECURITY RESEARCHER analyzing {target}.
Current URL: {scout.page.url}
Strategic Plan (Attack Tree): {strategy}
Current Step: {i+1}/{total_intended}

Observe context: {dom}

Task: Perform a deep security interaction to identify vulnerabilities (IDOR, Broken Access Control, Logic Bugs).
Return ONLY a JSON object:
{{
  "type": "click" | "type" | "navigate",
  "selector": "css selector",
  "value": "payload value if typing",
  "vulnerability_target": "target area",
  "reasoning": "Scientific justification"
}}"""
                
                response = invoke_with_retry("deep_auditor", [HumanMessage(content=prompt)])
                action_data = safe_json_parse(response.content)
                
                if action_data:
                    selector = action_data.get("selector", "N/A")
                    payload = action_data.get("value", "")
                    
                    # Check memory
                    if db.was_tried(scout.page.url, selector, payload):
                        console.print(f"[yellow]🔄 Payload already tried on this selector. Asking for alternative...[/yellow]")
                        continue
                    
                    target_v = action_data.get("vulnerability_target", "Discovery")
                    console.print(f"[bold red]🚀 Testing {target_v} at {selector}...[/bold red]")
                    
                    success, result_msg = scout.perform_action(action_data)
                    
                    # Record result in memory
                    res_code = 200 if success else 500
                    db.record_attack(scout.page.url, selector, payload, res_code)
                    
                    if success:
                        success_count += 1
                        console.print(f"[dim]   - Integrity Check: {result_msg}[/dim]")
                    else:
                        console.print(f"[red]   - Check Blocked/Failed: {result_msg}[/red]")

            
        return {
            "dom_snapshot": str(dom),
            "captured_requests": scout.captured_requests,
            "browser_logs": scout.console_logs,
            "audit_status": "COMPLETE" if success_count > 0 else "PARTIAL",
            "coverage_score": success_count / total_intended
        }
    finally:
        try: scout.close()
        except: pass

def red_team_node(state: AgentState):
    """v7.4 - Red Team (Offensive Thinking). Find potential vulnerabilities."""
    console.print("[bold red]⚔️ RED TEAM is identifying exploit vectors...[/bold red]")
    
    requests = state.get("captured_requests", [])
    dom = state.get("dom_snapshot", "")
    
    prompt = f"""You are an ELITE PENTESTER. Find 3 potential vulnerabilities.
Evidence: {requests[:10]}
DOM: {dom[:5000]}
Return Findings in JSON list."""

    response = invoke_with_retry("deep_auditor", [HumanMessage(content=prompt)])
    return {"web_findings": safe_json_parse(response.content) or []}

def blue_team_node(state: AgentState):
    """v7.4 - Blue Team (Skeptical Critique). Filter out False Positives."""
    console.print("[bold blue]🛡️ BLUE TEAM (Skeptical Dev) is reviewing findings...[/bold blue]")
    
    findings = state.get("web_findings", [])
    if not findings: return {}
    
    prompt = f"""You are a SKEPTICAL SENIOR DEVELOPER. Review these 'potential' vulnerabilities.
Findings: {findings}
Identify False Positives and provide a Critique Score (0-100).
Return ONLY valid findings with Score > 80."""

    response = invoke_with_retry("deep_auditor", [HumanMessage(content=prompt)])
    validated = safe_json_parse(response.content) or []
    
    return {"target_vulns": validated, "reports": [response.content]}

def explorer_node(state: AgentState):
    console.print("[bold cyan]📂 Indexing project structure...[/bold cyan]")
    repo_path = state["code_path"]
    
    # 1. Detect Project Root (Monorepo handling)
    # Search for foundry.toml or package.json
    project_root = repo_path
    config_files = list(repo_path.rglob("foundry.toml")) + list(repo_path.rglob("package.json"))
    
    if config_files:
        # Pick the most "relevant" root (default to the first one found, often 'contracts/')
        project_root = config_files[0].parent
        console.print(f"[green]🎯 Detected Solidity project root: {project_root.relative_to(repo_path)}[/green]")
    
    # 2. v5.5 Submodule & Dependency Master
    if (repo_path / ".gitmodules").exists():
        console.print("[bold yellow]📦 Git Submodules detected. Synchronizing libraries...[/bold yellow]")
        run_cmd(["git", "submodule", "update", "--init", "--recursive"], cwd=repo_path, timeout=300)
    
    # Run forge install in the project root to be safe
    if (project_root / "foundry.toml").exists():
        console.print("[bold yellow]🔨 Running 'forge install' to ensure dependencies...[/bold yellow]")
        run_cmd(["forge", "install"], cwd=project_root, timeout=300)

    # 3. Detect Source Directory (src vs contracts)
    source_dir = "src"
    if (project_root / "contracts").exists() and (project_root / "contracts").is_dir():
        source_dir = "contracts"
    elif (project_root / "src").exists():
        source_dir = "src"
    
    # 3. Normalize in_scope_patterns (v5.1 Scope-Normalizer)
    # If the user input 'contracts/src' but project_root is 'contracts', normalize to 'src'
    normalized_scope = []
    project_rel_path = str(project_root.relative_to(repo_path))
    for pattern in state.get("in_scope_patterns", []):
        if project_rel_path != "." and pattern.startswith(project_rel_path):
            cleaned = pattern[len(project_rel_path):].strip("/")
            if cleaned: normalized_scope.append(cleaned)
        else:
            normalized_scope.append(pattern)
    
    # 4. Index Structure
    files = []
    exclude_dirs = {".git", "node_modules", "lib", "out", "cache", "broadcast"}
    for path in project_root.rglob("*.sol"):
        if not any(excluded in path.parts for excluded in exclude_dirs):
            files.append(str(path.relative_to(project_root)))
            
    return {
        "project_root": project_root,
        "source_dir": source_dir,
        "in_scope_patterns": normalized_scope,
        "project_structure": "\n".join(files)
    }

def intent_node(state: AgentState):
    console.print("[bold magenta]📖 Analyzing documentation...[/bold magenta]")
    doc_content = ""
    for doc_name in ["README.md", "docs/OVERVIEW.md", "docs/index.md"]:
        doc_path = state["code_path"] / doc_name
        if doc_path.exists():
            doc_content += doc_path.read_text(encoding="utf-8")[:4000]
    
    if not doc_content:
        return {"intent_summary": "No documentation found."}
        
    prompt = f"Analyze the following documentation to identify core protocol Invariants and main Actors/Roles:\n\n{doc_content}"
    response = invoke_with_retry("fast_analyzer", [HumanMessage(content=prompt)])
    return {"intent_summary": response.content}

def librarian_node(state: AgentState):
    """Scan the knowledge base and inject relevant project-specific security intelligence."""
    console.print("[bold yellow]📚 The Librarian is fetching security intelligence...[/bold yellow]")
    
    knowledge_path = Path("knowledge")
    if not knowledge_path.exists():
        console.print("[yellow]⚠️ Warning: /knowledge directory not found. Librarian will have no context.[/yellow]")
        return {"security_knowledge": "No local knowledge base found."}

        
    all_knowledge = ""
    # Support multiple formats: .md, .txt, .json, .pdf, .sol
    # Use rglob for RECURSIVE scanning (finds files in subfolders like defihacklab/test/2024-xx/)
    extensions = ["*.md", "*.txt", "*.json", "*.pdf", "*.sol"]
    knowledge_files = []
    for ext in extensions:
        knowledge_files.extend(knowledge_path.rglob(ext))
        
    # Shuffle or limit to avoid reading the same files every time if there are too many
    # For now, we prioritize by keyword matching
    
    intent = state.get("intent_summary", "").lower()
    # Expanded keywords for DeFiHackLabs
    keywords = ["vault", "lend", "borrow", "pool", "swap", "bridge", "defi", "stable", "price", "oracle", "reentrancy", "flashloan", "sandwich"]
    
    found_count = 0
    for file in knowledge_files:
        if found_count > 10: break # Limit to top 10 most relevant files to save context
        
        file_name_lower = file.name.lower()
        is_relevant = any(kw in file_name_lower for kw in keywords) or any(kw in intent for kw in keywords)
        
        # Always include core pitfalls
        if is_relevant or file_name_lower in ["solidity_pitfalls.md", "security_checklists.md"]:
             console.print(f"[dim yellow]   - Knowledge found: {file.name}[/dim yellow]")
             try:
                 if file.suffix == ".pdf":
                     reader = PdfReader(file)
                     content = ""
                     for page in reader.pages:
                         content += page.extract_text() + "\n"
                     all_knowledge += f"\n--- INTELLIGENCE (PDF): {file.name} ---\n{content}\n"
                 else:
                     # Text-based (md, txt, json, sol)
                     content = file.read_text(encoding="utf-8")
                     all_knowledge += f"\n--- INTELLIGENCE: {file.name} ---\n{content}\n"
                 found_count += 1
             except Exception as e:
                 console.print(f"[red]Error reading {file.name}: {e}[/red]")
             
    return {"security_knowledge": all_knowledge[:30000]} # Increased limit to 30k for richer intelligence

def invariant_miner_node(state: AgentState):
    """Hypothesize system-wide invariants and attack vectors based on intent and structure."""
    console.print("[bold red]⛏️ Mining Critical Protocol Invariants...[/bold red]")
    
    prompt = f"""As a Senior Security Researcher, analyze the project structure and intent to identify the TOP 5 CRITICAL INVARIANTS that MUST hold true to prevent a catastrophic exploit (e.g., loss of all funds, drain of collateral).

INTENT: {state['intent_summary']}
STRUCTURE: {state['project_structure']}

Return internal logical conditions or mathematical invariants. 
Focus on: Asset Safety, Solvency, Access Control, and Logical State Consistency."""

    response = invoke_with_retry("deep_auditor", [HumanMessage(content=prompt)])
    return {"project_invariants": response.content}

def core_context_ingestor_node(state: AgentState):
    """Ingest source code of all core contracts from the project root."""
    console.print("[bold cyan]📥 Ingesting Core Project Context (Monorepo-Safe)...[/bold cyan]")
    project_root = state.get("project_root", state["code_path"])
    in_scope_patterns = state.get("in_scope_patterns", [])
    all_core_code = ""
    exclude_dirs = {".git", "node_modules", "lib", "out", "cache", "broadcast", "test"}
    
    sol_files = []
    for path in project_root.rglob("*.sol"):
        if path.is_file() and not any(excluded in path.parts for excluded in exclude_dirs):
            sol_files.append(path)
            
    # Sort by size but prioritize in-scope files
    sol_files.sort(key=lambda x: x.stat().st_size, reverse=True)
    
    for path in sol_files[:12]:
            
        rel_path = str(path.relative_to(project_root))
        is_in_scope = not in_scope_patterns or any(pattern in rel_path for pattern in in_scope_patterns)
        tag = "[IN-SCOPE]" if is_in_scope else "[OUT-OF-SCOPE/CONTEXT-ONLY]"
        
        content = path.read_text(encoding="utf-8")
        all_core_code += f"\n--- FILE: {rel_path} {tag} ---\n{content}\n"
        
    return {"core_code_context": all_core_code}

def fuzz_engineer_node(state: AgentState):
    """Generate a comprehensive Foundry Invariant Test (ArsenalInvariants.t.sol)."""
    console.print("[bold green]🧪 Engineering Foundry Invariants (Fuzzing Architect)...[/bold green]")
    source_dir = state.get("source_dir", "src")
    
    prompt = f"""Write a single Foundry Invariant Test file (ArsenalInvariants.t.sol) to test the following hypothesized invariants.
INVARIANTS: {state['project_invariants']}
CORE CONTEXT: {state['core_code_context'][:20000]}

Requirements:
1. Inherit from 'Test' (forge-std/Test.sol).
2. Set up target contracts in the 'setUp()' function.
3. IMPORTANT: Your imports should point to ../{source_dir}/ContractName.sol based on the context.
4. Implement functions starting with 'invariant_' that assert the Hypothesis.
5. SOLIDITY SYNTAX RULE: DO NOT use 'calldata' for state variables or memory allocations. Use 'memory' or 'bytes' where appropriate.
6. ANTI-HALLUCINATION RULE: ONLY use interfaces or contracts that exist in the CORE CONTEXT. DO NOT invent arbitrary contracts.
7. Return ONLY the code block starting with ```solidity."""

    # 5. Execute Fuzzing Architect
    response = invoke_with_retry("fuzz_engineer", [HumanMessage(content=prompt)])
    content = response.content.strip()
    if "```solidity" in content:
        code = content.split("```solidity")[-1].split("```")[0].strip()
    else:
        code = content.strip()
    return {"invariant_test_code": code}

def fuzz_executor_node(state: AgentState):
    """Execute the invariant tests via Forge Fuzzing."""
    project_root = state.get("project_root", state["code_path"])
    test_dir = project_root / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / "ArsenalInvariants.t.sol"
    test_file.write_text(state["invariant_test_code"], encoding="utf-8")
    
    console.print(f"[bold white on blue]🚀 Running Invariant Fuzzing ({Config.FUZZ_RUNS} runs)...[/bold white on blue]")
    success, output = run_cmd([
        "forge", "test", 
        "--match-path", str(test_file.relative_to(project_root)),
        "--fuzz-runs", str(Config.FUZZ_RUNS),
        "--no-ffi", "--no-cache" # v11.0 Security Hardening
    ], cwd=project_root, timeout=300)


    
    return {"fuzz_logs": output if not success else "All Invariants Passed."}

def slither_node(state: AgentState):
    console.print("[bold blue]🐍 Running Slither (Structural Context)...[/bold blue]")
    project_root = state.get("project_root", state["code_path"])
    success, output = run_cmd_with_retry(["slither", ".", "--json", "-"], cwd=project_root, timeout=Config.TIMEOUTS["slither"])
    return {"slither_output": output if success else "{}"}


def aderyn_node(state: AgentState):
    """Run Aderyn for modern static analysis and gas findings."""
    project_root = state.get("project_root", state["code_path"])
    if not check_tool("aderyn"):
        return {"aderyn_output": "Aderyn not installed."}
    
    console.print("[bold cyan]🐦 Running Aderyn scanner...[/bold cyan]")
    report_file = project_root / "aderyn_report.json"
    success, _ = run_cmd_with_retry(["aderyn", ".", "--output", str(report_file)], cwd=project_root, timeout=Config.TIMEOUTS["aderyn"])
    
    if success and report_file.exists():
        data = json.loads(report_file.read_text(encoding="utf-8"))
        return {"aderyn_output": json.dumps(data, indent=2)[:5000]}
    return {"aderyn_output": "Aderyn scan failed or no report generated."}


def surya_node(state: AgentState):
    """Use Surya to map contract interactions."""
    project_root = state.get("project_root", state["code_path"])
    if not check_tool("surya"):
        return {"surya_output": "Surya not installed."}
    
    console.print("[bold magenta]🗺️ Generating Call Graph with Surya...[/bold magenta]")
    # Find first non-library sol file to describe
    sol_files = [p for p in project_root.rglob("*.sol") if p.is_file()]
    if not sol_files:
        return {"surya_output": "No Solidity files found."}
        
    success, output = run_cmd_with_retry(["surya", "describe", str(sol_files[0])], cwd=project_root, timeout=Config.TIMEOUTS["surya"])
    return {"surya_output": output if success else "Surya fail."}


def consensus_node(state: AgentState):
    """Synthesize findings from different tools to pick multiple high-priority targets."""
    console.print("[bold green]⚖️ Consensus Triage...[/bold green]")
    
    # v10.3 Resilience: Handle empty tool outputs safely
    slither = state.get("slither_output", "") or "No findings"
    aderyn = state.get("aderyn_output", "") or "No findings"
    fuzz = state.get("fuzz_logs", "") or "No findings"
    
    prompt = f"""As a Chief Security Officer, synthesize results from these static tools and REAL-WORLD evidence:
1. SLITHER: {slither[:3000]}
2. ADERYN: {aderyn[:3000]}
3. SURYA (Call Graph): {state.get('surya_output', '')[:2000]}
4. INVARIANT FUZZING LOGS: {fuzz[:5000]}

Identify a list of high-risk or consensus vulnerabilities (max 3). 
PRIORITIZE issues that correlate with Invariant Fuzzing failures.


CRITICAL: 'contract' MUST be a specific RELATIVE PATH to a .sol file (e.g., 'src/Vault.sol'), NOT a directory (e.g., 'src/'). 
ONLY report vulnerabilities in the following IN-SCOPE paths:
{state.get('in_scope_patterns', 'ALL')}

Return ONLY a JSON array of objects:
[
  {{
    "type": "Vulnerability Type", 
    "contract": "Relative Path to .sol FILE", 
    "description": "Short explanation", 
    "confidence": "High/Med/Low"
  }},
  ...
]"""

    model_role = "triage"
    response = invoke_with_retry(model_role, [
        SystemMessage(content="You are a JSON-only response engine. Return perfect JSON array."),
        HumanMessage(content=prompt)
    ])
    
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[-1].split("```")[0].strip()
            
        vulns = json.loads(content)
        if not isinstance(vulns, list):
            vulns = [vulns]
        return {"target_vulns": vulns, "current_index": 0, "retry_count": 0}
    except Exception as e:
        logger.error(f"Failed to parse consensus JSON: {e}")
        return {"target_vulns": [], "current_index": 0, "retry_count": 0}

def mythril_node(state: AgentState):
    """Deep Symbolic Analysis on the targeted contract."""
    if state["current_index"] >= len(state["target_vulns"]):
        return {"mythril_output": "N/A"}

    project_root = state.get("project_root", state["code_path"])
    vuln = state["target_vulns"][state["current_index"]]
    
    # v12.0 Prioritize system 'myth' over hardcoded venv paths
    myth_cmd = shutil.which("myth") or Config.MYTHRIL_PATH
    
    contract_path = project_root / vuln["contract"]
    if not contract_path.exists() or contract_path.is_dir():
        # Fallback: if dir, ignore or skip Mythril for this specific target
        return {"mythril_output": f"Contract {vuln['contract']} is a directory or missing. Skipping Mythril."}

    console.print(f"[bold red]🛡️ Deep Symbolic Analysis (Mythril) on {vuln['contract']}...[/bold red]")
    success, output = run_cmd_with_retry([str(myth_cmd), "analyze", str(contract_path), "-o", "jsonv2"], cwd=project_root, timeout=Config.TIMEOUTS["mythril"])
    return {"mythril_output": output[:5000]}


def auditor_node(state: AgentState):
    """Final Reasoning Audit based on all collected tool data and code context."""
    if not state.get("target_vulns") or state["current_index"] >= len(state["target_vulns"]):
        console.print("[yellow]⚠️ No target vulnerabilities to audit. Moving to report...[/yellow]")
        return {"reports": state.get("reports", [])}

    project_root = state.get("project_root", state["code_path"])
    vuln = state["target_vulns"][state["current_index"]]
    contract_path = project_root / vuln["contract"]
    def get_recursive_context(file_path: Path, visited: set, depth: int = 0, max_depth: int = 5) -> str:
        """v11.0 - Safety-first recursive context gathering with depth limits and enhanced parsing."""
        if depth > max_depth: return ""
        file_path = file_path.resolve()
        if file_path in visited: return ""
        visited.add(file_path)
        
        if not file_path.exists(): return ""
        
        try:
            content = file_path.read_text(encoding="utf-8")
            context = f"\n--- FILE: {file_path.relative_to(project_root)} ---\n{content}\n"
            
            # v11.0 Enhanced Regex for imports (supports {Contract} from "path")
            import_patterns = [
                r'import\s+["\']([^"\']+)["\']',
                r'import\s+{[^}]+}\s+from\s+["\']([^"\']+)["\']'
            ]
            
            import re
            imports = []
            for pattern in import_patterns:
                imports.extend(re.findall(pattern, content))

            for imp in imports:
                imp_path = file_path.parent / imp
                if not imp_path.exists():
                    # Fallback: search in project root if relative path fails
                    found = list(project_root.rglob(imp))
                    if found: imp_path = found[0]
                
                if imp_path.exists() and imp_path.is_file():
                    context += get_recursive_context(imp_path, visited, depth + 1, max_depth)
            return context
        except:
            return ""


    code_content = ""
    
    if contract_path.exists() and not contract_path.is_dir():
        code_content = get_recursive_context(contract_path, set())
    elif contract_path.is_dir():
         potential_file = contract_path / (contract_path.name + ".sol")
         if potential_file.exists():
             code_content = get_recursive_context(potential_file, set())
             vuln["contract"] = str(potential_file.relative_to(project_root))
         else:
             code_content = "[DIRECTORY UPLOADED - NO FILE FOUND]"
    
    console.print(f"[bold red]🔍 Final Reasoning Audit for {vuln['type']} in {vuln['contract']} (v6.0 R1 Active)...[/bold red]")
    
    feedback_context = f"\nPREVIOUS FAILURE LOGS:\n{state.get('logs', '')}" if state.get('logs') else ""
    
    prompt = f"""CODE AUDIT REQUEST (Ultimate v6.0 Cross-contract Analysis):
Target: {vuln['contract']} ({vuln['type']})
Project Invariants: {state.get('project_invariants', 'N/A')}
Fuzzing Evidence (CRITICAL): {state.get('fuzz_logs', 'N/A')}
Security Knowledge/Intelligence: {state.get('security_knowledge', 'N/A')}
Protocol Intent: {state['intent_summary']}
Static Findings: {vuln['description']}
Mythril Deep Scan: {state.get('mythril_output', 'N/A')}
{feedback_context}

FULL CONTRACT CONTEXT (Target + Imports):
```solidity
{code_content}

Perform a deep system-wide analysis. 
1. Use the Fuzzing Evidence to prove the vulnerability exists.
2. Explain how this vulnerability breaks specified Invariants.
3. Provide a step-by-step exploit scenario."""
    
    response = invoke_with_retry("deep_auditor", [HumanMessage(content=prompt)])
    return {"messages": [response], "logs": ""}

def poc_engineer_node(state: AgentState):
    """Generate a Foundry PoC for the confirmed vulnerability with feedback loop awareness."""
    if not state.get("messages") or not state.get("target_vulns") or state["current_index"] >= len(state["target_vulns"]):
        return {"poc_code": "N/A"}
        
    audit_reasoning = state["messages"][-1].content
    console.print(f"[bold green]🧪 Engineering Foundry PoC (Attempt {state.get('retry_count', 0) + 1})...[/bold green]")
    
    feedback_prompt = ""
    if state.get("logs"):
        feedback_prompt = f"\n\nCRITICAL ERROR FEEDBACK (Attempt {state.get('retry_count', 0)} Failed):\n{state['logs']}\n\nINSTRUCTION: Analyze the error ABOVE. \n1. If 'Identifier not found', you MUST either find the correct Import or explicitly DEFINE the missing interface (e.g., interface IContract { ... }) at the top of your test file.\n2. If 'Source not found', fix your import paths (check if it should be ../src/ or ../contracts/).\n3. FOCUS on proving that 'Emergency Stop' fails (state should be paused but logic still executes)."


    prompt = f"""Write a Foundry exploit (ArsenalExploit.t.sol) for the following vulnerability.
Requirement: Inherit from 'Test' (forge-std/Test.sol).
SAFE-STRING RULE: DO NOT use emojis or non-ASCII characters in console.log or strings. Use only plain text.
HALLUCINATION GUARDRAIL: Verify that the contract you are targeting exists in the provided context. DO NOT invent contract names.
IMPORTANT: If you use complex interfaces from the project, define them at the top of the file to avoid 'Identifier not found' errors.
Audit Summary: {audit_reasoning}{feedback_prompt}

Return ONLY the code block starting with ```solidity."""
    
    response = invoke_with_retry("poc_generator", [HumanMessage(content=prompt)])
    content = response.content.strip()
    if "```solidity" in content:
        code = content.split("```solidity")[-1].split("```")[0].strip()
    else:
        code = content.strip()
    return {"poc_code": code}

def verificator_node(state: AgentState):
    """Verify the PoC by running forge test and capture detailed logs."""
    if state.get("poc_code") == "N/A":
        return {"verification_result": "SKIPPED", "logs": ""}
        
    project_root = state.get("project_root", state["code_path"])
    test_dir = project_root / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / "ArsenalExploit.t.sol"
    test_file.write_text(state["poc_code"], encoding="utf-8")
    
    console.print("[bold white on blue]🚀 Running Verification via Forge...[/bold white on blue]")
    success, output = run_cmd([
        "forge", "test", 
        "--match-path", str(test_file.relative_to(project_root)), 
        "-vv",
        "--no-ffi", "--no-cache" # v11.0 Security Hardening
    ], cwd=project_root, timeout=Config.TIMEOUTS["forge"])


    
    if not success:
        console.print(f"[bold red]❌ PoC Verification Failed! Error Log:[/bold red]\n{output}")
    else:
        console.print("[bold green]✅ PoC Verification SUCCESS (Vulnerability Confirmed!)[/bold green]")

    status = "SUCCESS (Vulnerability Confirmed)" if success else "FAILED"
    new_retry_count = state.get("retry_count", 0) + (1 if not success else 0)
    
    return {
        "verification_result": status, 
        "logs": output if not success else "",
        "retry_count": new_retry_count
    }

def reporter_node(state: AgentState):
    if not state.get("target_vulns") or state["current_index"] >= len(state["target_vulns"]):
        return {"reports": state.get("reports", []), "current_index": state["current_index"] + 1}
        
    vuln = state["target_vulns"][state["current_index"]]
    verif_status = state.get("verification_result", "FAILED")
    
    honesty_instruction = ""
    if state.get("audit_status") != "COMPLETE":
        honesty_instruction = f"IMPORTANT: The audit was {state.get('audit_status', 'PARTIAL')} with {state.get('coverage_score', 0)*100}% coverage. You MUST start the finding by stating that the audit was incomplete and some logic paths were not tested."
    elif "FAILED" in verif_status:
        honesty_instruction = "IMPORTANT: The PoC verification FAILED. Label as [THEORETICAL FINDING]."
    else:
        honesty_instruction = "IMPORTANT: The PoC verification SUCCESSFUL. Label as [CONFIRMED VULNERABILITY]."

    prompt = f"""Generate a Pro Security Finding:
{honesty_instruction}
Target: {vuln.get('contract', 'N/A')} ({vuln.get('type', 'N/A')})
Description: {vuln.get('description', 'N/A')}
Audit Reasoning: {state['messages'][-1].content[:5000]}
PoC Verification Status: {verif_status}
Foundry Test:
```solidity
{state.get('poc_code', 'N/A')}
```"""

    model_role = "report_writer"
    response = invoke_with_retry(model_role, [HumanMessage(content=prompt)])
    current_reports = state.get("reports", [])
    current_reports.append(response.content)
    
    return {"reports": current_reports, "current_index": state["current_index"] + 1, "retry_count": 0, "logs": ""}

def reviewer_node(state: AgentState):
    """Review findings for quality and potential false positives before final aggregation."""
    if not state["reports"]: return {"reports": []}
    
    console.print(f"[bold yellow]🧬 Reviewing Found Vulnerabilities (Reviewer Node)...[/bold yellow]")
    current_report = state["reports"][-1]
    
    prompt = f"""You are a Senior Security Auditor. Review the following finding for accuracy, impact assessment, and PoC validity.
FINDING:
{current_report}

Identify any errors or inconsistencies. If the finding is solid, respond with 'QUALIFIED'. 
Otherwise, suggest improvements or mark as 'FALSE POSITIVE'.
RESPONSE FORMAT: Start with 'REVIEW STATUS: [QUALIFIED/IMPROVMENT NEEDED/FALSE POSITIVE]' following by your feedback."""

    model_role = "reviewer"
    response = invoke_with_retry(model_role, [HumanMessage(content=prompt)])
    # Append review to the last report
    updated_report = current_report + f"\n\n### 🛡️ Peer Review Result\n{response.content}"
    state["reports"][-1] = updated_report
    return {"reports": state["reports"]}

def human_review_node(state: AgentState):
    """v10.0 - HITL Pause. Wait for the human co-pilot to approve strategy or inject data."""
    # v14.4 Critical Stability: Ensure dashboard is GONE before printing anything
    if Config.DASHBOARD: 
        Config.DASHBOARD.stop()
        console.clear()
        
    Config.CURRENT_PHASE = "⏸️ WAITING FOR HUMAN REVIEW..."

    
    console.print("\n[bold red]🛑 ARSENAL IS PAUSED FOR STRATEGIC REVIEW[/bold red]")
    console.print(f"[bold yellow]Strategic Attack Tree generated in attack_strategy.md[/bold yellow]")
    console.print("[dim]v10.2 Tip: To handle logins, ensure SHOW_BROWSER=True in .env. Log in manually when paused, then press ENTER.[/dim]")
    # v14.3 Robustness: Stop Live Dashboard before input() to prevent UI flickering
    if Config.DASHBOARD: Config.DASHBOARD.stop()
    
    user_input = input(">>> Press ENTER to continue or type custom instructions: ").strip()
    
    # Restart if needed
    if Config.DASHBOARD: 
        Config.DASHBOARD.start()
        Config.DASHBOARD.update("Human review complete. Resuming audit...")
    
    if user_input:
        console.print(f"[bold blue]💡 Human Instruction received: {user_input}[/bold blue]")
        return {"logs": state.get("logs", "") + f"\n[Human Instruction]: {user_input}", "last_node": "human_review"}
        
    return {"last_node": "human_review"}



def protocol_mapper_node(state: AgentState):
    """v8.0 - Protocol Architect (The Whitepaper Mind). Extracts Business Logic Invariants."""
    console.print("[bold yellow]📜 PROTOCOL ARCHITECT is mapping business logic...[/bold yellow]")
    
    repo_path = state["code_path"]
    # Read READMEs and core interfaces
    docs = []
    for ext in ["md", "sol"]:
        for f in repo_path.rglob(f"*.{ext}"):
            if "test" not in f.name.lower():
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        docs.append(f"File: {f.name}\n{file.read()[:2000]}")
                except: pass
    
    prompt = f"""You are a PROTOCOL ARCHITECT. Analyze the following documentation and code.
Map out the CORE BUSINESS LOGIC and FINANCIAL INVARIANTS.
Identify the 'Flow of Funds' and sensitive state variables.
Output high-level logic constraints (e.g., 'A user's debt should never decrease without a payment')."""

    model_role = "deep_auditor"
    response = invoke_with_retry(model_role, [HumanMessage(content=prompt)])
    
    return {"business_logic": response.content}


def final_aggregator_node(state: AgentState):
    """v8.0 - Professional Reporter (Immunefi Standard). Overall findings and LoF analysis."""
    console.print("[bold green]📄 PROFESSIONAL REPORTER is generating Immunefi-standard report...[/bold green]")
    
    findings = state.get("target_vulns", [])
    web_findings = state.get("web_findings", [])
    invariants = state.get("project_invariants", "N/A")
    
    prompt = f"""You are a SENIOR SECURITY RESEARCHER on Immunefi.
Generate a professional security report based on:
1. Business Logic Map: {invariants}
2. Smart Contract Findings: {findings}
3. Web/Logic Findings: {web_findings}

Follow Immunefi V2.1 Standard:
- TITLE & SEVERITY (Critical/High/Medium/Low)
- IMPACT (Detailed Economic Analysis / Loss of Funds)
- ROOT CAUSE
- PROOF OF CONCEPT (Must be reproducible via Forge)
- REMEDIATION"""

    model_role = "deep_auditor"
    response = invoke_with_retry(model_role, [HumanMessage(content=prompt)])
    
    # Save the professional report
    with open("Immunefi_Professional_Report.md", "w", encoding="utf-8") as f:
        f.write("# 🛡️ ARSENAL SECURITY v8.0 PRO REPORT\n\n")
        f.write(response.content)
        
    return {"reports": [response.content]}

# ====================== Graph Construction ======================

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("environment_check", environment_check_node)
workflow.add_node("triage_target", triage_target_node)
workflow.add_node("wildcard_recon", wildcard_recon_node)
workflow.add_node("web_recon", web_recon_node)
workflow.add_node("web_scan", web_scan_node)
workflow.add_node("human_review", human_review_node)
workflow.add_node("auth_gate", auth_gate_node)
workflow.add_node("protocol_mapper", protocol_mapper_node)
workflow.add_node("librarian", librarian_node) # Web3 Librarian
workflow.add_node("librarian_rag", librarian_rag_node) # Web2 Librarian
workflow.add_node("commander", commander_node)

# v13.0 Expanded Web2 specialist nodes
workflow.add_node("js_analyst", js_analyst_node)
workflow.add_node("param_miner", param_miner_node)
workflow.add_node("fuzzer", fuzzer_node)
workflow.add_node("injection_expert", injection_expert_node)


workflow.add_node("interactive_scout", interactive_scout_node)
workflow.add_node("red_team", red_team_node)
workflow.add_node("blue_team", blue_team_node)
workflow.add_node("mobile_static", mobile_static_node)
workflow.add_node("explorer", explorer_node)
workflow.add_node("intent", intent_node)
workflow.add_node("invariant_miner", invariant_miner_node)
workflow.add_node("core_context_ingestor", core_context_ingestor_node)
workflow.add_node("fuzz_engineer", fuzz_engineer_node)
workflow.add_node("fuzz_executor", fuzz_executor_node)
workflow.add_node("slither", slither_node)
workflow.add_node("aderyn", aderyn_node)
workflow.add_node("surya", surya_node)
workflow.add_node("consensus", consensus_node)
workflow.add_node("mythril", mythril_node)
workflow.add_node("auditor", auditor_node)
workflow.add_node("poc_engineer", poc_engineer_node)
workflow.add_node("verificator", verificator_node)
workflow.add_node("report", reporter_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("final_aggregator", final_aggregator_node)

# v14.2 Specialist Nodes
workflow.add_node("logic_architect", logic_architect_node)


# Define Logic
def route_after_verification(state: AgentState):
    """Conditional edge: Retry? Next? or End?"""
    if state["verification_result"] == "FAILED" and state["retry_count"] < Config.MAX_RETRIES:
        console.print(f"[yellow]⚠️ PoC Failed. Retrying ({state['retry_count'] + 1}/{Config.MAX_RETRIES})...[/yellow]")
        return "retry"
    
    # Move to report generation for current finding
    return "report"

def route_after_review(state: AgentState):
    """Conditional edge: Process next finding?"""
    if state["current_index"] < len(state["target_vulns"]):
        console.print(f"[blue]🔄 Moving to next finding ({state['current_index'] + 1}/{len(state['target_vulns'])})...[/blue]")
        return "next"
    return "finish"

# Define Flow
def route_target(state: AgentState):
    """Route to specialized hunter based on target type."""
    t_type = state.get("target_type", "web3")
    if t_type == "wildcard": return "wildcard"
    if t_type == "web2": return "web"
    if t_type == "mobile": return "mobile"
    return "web3"

def route_human_review(state: AgentState):
    """Conditional edge: Where to go after manual review?"""
    # v14.3 Fix: Ensure we always return a valid route
    last = state.get("last_node", "")
    t_type = state.get("target_type", "")

    if "final_report" in state and state["final_report"]:
        return "finish"
        
    if last == "wildcard_recon":
        return "web_recon"
    
    # v14.4 If we are in Web2/Wildcard and finished initial stages, go to interactive
    if t_type in ["web2", "wildcard"]:
        return "interactive_scout"
    
    return "finish"


    return "web_recon" # Default


workflow.set_entry_point("environment_check")

workflow.add_edge("environment_check", "triage_target")


workflow.add_conditional_edges(
    "triage_target",
    route_target,
    {
        "web3": "protocol_mapper",
        "wildcard": "wildcard_recon",
        "web": "web_recon",
        "mobile": "mobile_static"
    }
)

# Web3 Pipeline (In-depth Security Audit Loop)
workflow.add_edge("protocol_mapper", "explorer")
workflow.add_edge("explorer", "intent")
workflow.add_edge("intent", "librarian")  # librarian maps to librarian_node for Web3
workflow.add_edge("librarian", "invariant_miner")
workflow.add_edge("invariant_miner", "core_context_ingestor")
workflow.add_edge("core_context_ingestor", "fuzz_engineer")
workflow.add_edge("fuzz_engineer", "fuzz_executor")
workflow.add_edge("fuzz_executor", "aderyn")
workflow.add_edge("aderyn", "slither")
workflow.add_edge("slither", "mythril")
workflow.add_edge("mythril", "surya") # Add missing surya for triage data
workflow.add_edge("surya", "consensus")  # Consensus identifies targets
workflow.add_edge("consensus", "auditor")    # Logic check
workflow.add_edge("auditor", "poc_engineer")
workflow.add_edge("poc_engineer", "verificator")


workflow.add_conditional_edges(
    "verificator",
    route_after_verification,
    {
        "retry": "poc_engineer",
        "report": "report"
    }
)

workflow.add_edge("report", "reviewer")

workflow.add_conditional_edges(
    "reviewer",
    route_after_review,
    {
        "next": "mythril", # Loop to next vulnerability
        "finish": "final_aggregator"
    }
)

# Other Pipelines (v13.0 Expansion)
workflow.add_edge("wildcard_recon", "human_review")
workflow.add_edge("web_recon", "js_analyst")
workflow.add_edge("js_analyst", "param_miner")
workflow.add_edge("param_miner", "librarian_rag")
workflow.add_edge("librarian_rag", "auth_gate")
workflow.add_edge("auth_gate", "fuzzer")
workflow.add_edge("fuzzer", "web_scan")
workflow.add_edge("web_scan", "logic_architect")
workflow.add_edge("logic_architect", "injection_expert")
workflow.add_edge("injection_expert", "commander")
workflow.add_edge("commander", "human_review")





workflow.add_conditional_edges(
    "human_review",
    route_human_review,
    {
        "web_recon": "web_recon",
        "interactive_scout": "interactive_scout",
        "finish": "final_aggregator"
    }
)


workflow.add_edge("interactive_scout", "red_team")
workflow.add_edge("red_team", "blue_team")
workflow.add_edge("blue_team", "final_aggregator")
workflow.add_edge("mobile_static", "consensus")

# Global Termination
workflow.add_edge("final_aggregator", END)


# Persistence layer (v12.0 SQLITE Resettable)
conn = sqlite3.connect("arsenal_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
app = workflow.compile(checkpointer=checkpointer)


def extract_rel_path_from_github_url(url: str) -> str:
    """Extract the relative path from a GitHub tree/blob URL."""
    if not url.startswith("http") or "github.com" not in url:
        return url
    
    # Handle /tree/<branch_or_commit>/<path> or /blob/<branch_or_commit>/<path>
    parts = url.split("/")
    if "tree" in parts:
        try:
            idx = parts.index("tree")
            return "/".join(parts[idx+2:])
        except: return url
    elif "blob" in parts:
        try:
            idx = parts.index("blob")
            return "/".join(parts[idx+2:])
        except: return url

    
    return url

# ====================== Main Execution ======================
import argparse

def run_arsenal_audit(repo_url: str, config: dict, scope: Optional[List[str]] = None):
    console.print(Panel.fit("🛡️ ARSENAL ELITE HUNTER v11.0 (Robustness Engine)", style="bold green"))

    
    # v7.2 Persistence Init
    HistoryDB() 
    
    target_path = Path("temp_repo")
    try:
        is_git = "github.com" in repo_url or "gitlab.com" in repo_url
        is_file = Path(repo_url).exists() and Path(repo_url).is_file()
        
        if is_git:
            # 1. Clean & Clone
            if target_path.exists():
                console.print("[yellow]Cleaning up old repository...[/yellow]")
                import shutil
                shutil.rmtree(target_path, ignore_errors=True)
            
            console.print(f"[blue]Cloning {repo_url}...[/blue]")
            success, clone_out = run_cmd(["git", "clone", "--recursive", repo_url, str(target_path)])
            if not success:
                console.print(f"[bold red]Clone failed:[/bold red] {clone_out}")
                return

            # 2. Project Pre-flight (Forge install deps)
            if (target_path / "foundry.toml").exists():
                console.print("[cyan]Foundry project detected. Installing dependencies...[/cyan]")
                run_cmd(["forge", "install"], cwd=target_path)
            elif (target_path / "package.json").exists():
                console.print("[cyan]Node.js/Hardhat project detected. Running npm install...[/cyan]")
                run_cmd(["npm", "install"], cwd=target_path)
            
            project_root = target_path
        elif is_file:
            target_path = Path(repo_url)
            project_root = target_path.parent # v12.0 Fix for local files
            console.print(f"[blue]Targeting local file: {target_path} (Root: {project_root})[/blue]")
        else:
            project_root = target_path
            console.print(f"[blue]Targeting Web URL: {repo_url}[/blue]")

        initial_state = {
            "repo_url": repo_url,
            "code_path": target_path,
            "project_root": project_root,

            "source_dir": "src",
            "project_structure": "",
            "intent_summary": "",
            "in_scope_patterns": scope if scope else [],
            "security_knowledge": "",
            "current_index": 0,
            "retry_count": 0,
            "reports": [],
            "target_vulns": [],
            "logs": "",
            "dom_snapshot": "",
            "browser_logs": [],
            "captured_requests": [],
            "audit_status": "Starting...",
            "aderyn_output": "",
            "slither_output": "",
            "mythril_output": "",
            "fuzz_logs": "",
            "invariant_test_code": "",
            "verification_result": "",
            "current_thought": "Starting the Arsenal Security Audit..."
        }

        
        final_state = initial_state
        
        # Run Graph via stream
        for event in app.stream(initial_state, config):
            for node_name, output in event.items():
                # v13.1 Robustness: Skip metadata or non-dict outputs to prevent TypeError
                if not output or not isinstance(output, dict):
                    continue
                    
                Config.CURRENT_PHASE = f"🚀 Executing {node_name.replace('_', ' ').upper()}"
                
                # v14.2 Propagate thinking to dashboard
                thought = output.get("current_thought", final_state.get("current_thought", ""))
                if Config.DASHBOARD: Config.DASHBOARD.update(thought)
                
                final_state.update(output)

                
                if "target_vulns" in output:
                    Config.FOUND_VULNS_COUNT = len(output["target_vulns"])


        console.print("[bold green]✅ Audit Analysis Complete![/bold green]")
        return final_state
        
    finally:
        # v11.0 Always cleanup temp repo if it was a git clone
        if "github.com" in repo_url or "gitlab.com" in repo_url:
            if target_path.exists():
                console.print("[yellow]Finalizing: Cleaning up temporary resources...[/yellow]")
                import shutil
                shutil.rmtree(target_path, ignore_errors=True)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Arsenal Bug Hunter v4.6 (Scope-Smart)")
    parser.add_argument("target", help="GitHub repo URL")
    parser.add_argument("--scope", help="Comma-separated list of in-scope folders/files (can be GitHub URLs)", default="")
    args = parser.parse_args()
    
    # Process scope: Handle both local paths and GitHub URLs
    raw_scope = [s.strip() for s in args.scope.split(",") if s.strip()]
    scope_list = [extract_rel_path_from_github_url(s) for s in raw_scope]
    
    # v10.0 Co-Pilot Launch
    os.environ["TARGET_URL"] = args.target
    if Config.DASHBOARD: Config.DASHBOARD.start()
    
    thread_config = {"configurable": {"thread_id": "arsenal_session_1"}}
    
    try:
        # Run the environment check first
        initial_state = run_arsenal_audit(args.target, thread_config, scope_list)
    finally:
        if Config.DASHBOARD: Config.DASHBOARD.stop()
