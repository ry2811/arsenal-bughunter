#!/usr/bin/env bash
set -e

cd /home/super/web3-bug-hunter
source venv/bin/activate

echo "=== Installing missing packages ==="
pip install rich --quiet

echo ""
echo "=== Checking Python syntax ==="
python3 -c "
import ast, sys
with open('audit_agent.py', 'r') as f:
    src = f.read()
ast.parse(src)
print('Syntax OK')
"

echo ""
echo "=== Checking critical imports ==="
python3 -c "
import os, sys, pathlib, subprocess, json, logging, glob, operator
from pathlib import Path
from typing import TypedDict, Annotated, List, Optional, Dict, Any
print('stdlib imports OK')

from dotenv import load_dotenv
print('dotenv OK')

from rich.console import Console
from rich.panel import Panel
print('rich OK')

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, END
print('langchain/langgraph OK')
"
echo ""
echo "=== All checks passed! ==="
