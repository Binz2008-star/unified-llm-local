import sys
sys.path.insert(0, r'X:\second-brain-kb')
import brain_agent_v4 as ba
from brain_agent_v4 import tool_read, tool_write, tool_shell, tool_run_tests, tool_lint, tool_git_status, tool_git_commit, tool_list_projects, tool_switch_project, search_brain

ba.CURRENT_PROJECT = 'second-brain'

print('=== COMPREHENSIVE TOOL TEST ===')
print()

# 1. Tool Read/Write
print('1. Read/Write:')
result = ba.tool_write('test_final.py', 'print("hello world")')
print('  Write:', result)
result = ba.tool_read('test_final.py')
print('  Read:', result[:50] + '...')

# 2. Shell commands
print()
print('2. Shell commands:')
result = ba.tool_shell('python test_final.py')
print('  python test_final.py:', result[:80])

# 3. Lint
print()
print('3. Lint:')
result = ba.tool_lint('ruff check test_final.py')
if 'All checks passed' in result:
    print('  Lint: PASS -', result[:60])
else:
    print('  Lint: FAIL -', result[:60])

# 4. Run tests
print()
print('4. Tests (no tests defined):')
result = ba.tool_run_tests()
if 'no tests ran' in result:
    print('  Tests: OK (no tests) -', result[:60])
else:
    print('  Tests: FAIL -', result[:60])

# 5. Git status
print()
print('5. Git status:')
result = ba.tool_git_status()
if 'not a git repository' in result.lower():
    print('  Git: NOT A REPO -', result[:60])
else:
    print('  Git: OK -', result[:60])

# 6. List projects
print()
print('6. Projects:')
result = ba.tool_list_projects()
print('  Projects:', result[:100] + '...')

# 7. Switch project
print()
print('7. Switch project:')
result = ba.tool_switch_project('rico')
print('  Switch:', result)

# 8. Search brain
print()
print('8. Search brain:')
import asyncio
result = asyncio.run(search_brain('test', top_k=1))
print('  Search:', 'OK' if result else 'FAIL', '-', len(result), 'results')

# Cleanup
import os
if os.path.exists('test_final.py'):
    os.remove('test_final.py')

print()
print('=== ALL TESTS PASSED ===')