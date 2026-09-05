import sys
sys.path.insert(0, r'X:\second-brain-kb')
import mcp_server_v4

import asyncio

async def test_mcp():
    print('Testing MCP server...')
    
    # Test list_tools
    class MockContext:
        pass
    
    ctx = MockContext()
    
    # Test list_tools
    result = await mcp_server_v4._handle_list_tools(None, None)
    print('Tools available:')
    for tool in result.tools:
        print(f'  - {tool.name}: {tool.description[:60]}...')
    
    # Need to create test files first
    import brain_agent_v4 as ba
    ba.CURRENT_PROJECT = 'second-brain'
    ba.tool_write('test_patch.py', 'print("hello")')
    ba.tool_write('test_replace.py', 'hello')
    
    # Test call_tool for apply_patch
    class MockParams:
        name = 'apply_patch'
        arguments = {
            'target_file': 'test_patch.py', 
            'patch_content': '--- test_patch.py\n+++ test_patch.py\n@@ -1,1 +1,2 @@\n print("hello")\n+print("world")'
        }
    
    class MockParams2:
        name = 'replace_block'
        arguments = {
            'target_file': 'test_replace.py', 
            'search_block': 'hello', 
            'replace_block': 'world'
        }
    
    class MockParams3:
        name = 'replace_block'
        arguments = {
            'target_file': 'nonexistent.py', 
            'search_block': 'hello', 
            'replace_block': 'world'
        }
    
    class MockParams4:
        name = 'list_memory'
        arguments = {'limit': 5}

    # Test apply_patch
    params = type('Params', (), {'name': 'apply_patch', 'arguments': {
        'target_file': 'test_patch.py', 
        'patch_content': '--- test_patch.py\n+++ test_patch.py\n@@ -1,1 +1,2 @@\n print("hello")\n+print("world")'
    }})()
    
    result = await mcp_server_v4._handle_call_tool(None, params)
    print('apply_patch result:', result.content[0].text[:100])
    
    # Test replace_block
    params2 = type('Params', (), {'name': 'replace_block', 'arguments': {
        'target_file': 'test_replace.py', 
        'search_block': 'hello', 
        'replace_block': 'world'
    }})()
    
    result2 = await mcp_server_v4._handle_call_tool(None, params2)
    print('replace_block result:', result2.content[0].text[:100])
    
    # Test replace_block on nonexistent file
    params3 = type('Params', (), {'name': 'replace_block', 'arguments': {
        'target_file': 'nonexistent.py', 
        'search_block': 'hello', 
        'replace_block': 'world'
    }})()
    
    result3 = await mcp_server_v4._handle_call_tool(None, params3)
    print('replace_block (nonexistent):', result3.content[0].text[:100])
    
    # Test list_memory
    params4 = type('Params', (), {'name': 'list_memory', 'arguments': {'limit': 5}})()
    
    result4 = await mcp_server_v4._handle_call_tool(None, params4)
    print('list_memory result:', result4.content[0].text[:100])

asyncio.run(test_mcp())