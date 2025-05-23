#!/usr/bin/env python3
"""
MCP Client Example
Version: 1.0
Date: May 23, 2025

Example client for the multi-jurisdiction MCP server.
"""

import aiohttp
import asyncio
import json
import argparse

class MCPClient:
    def __init__(self, endpoint="http://localhost:8000/mcp"):
        self.endpoint = endpoint
        
    async def request(self, method, params=None):
        """Send a request to the MCP server"""
        if params is None:
            params = {}
            
        request_data = {
            "method": method,
            "params": params
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint, json=request_data) as response:
                return await response.json()

async def example_jurisdiction_comparison():
    """Example comparing multiple jurisdictions"""
    
    client = MCPClient()
    
    # Compare jurisdictions
    print("Comparing parking requirements across jurisdictions...")
    compare_result = await client.request('compare', {
        'query': 'parking requirements for commercial buildings',
        'jurisdictions': ['Oregon/gresham', 'Oregon/multnomah_county'],
        'max_length': 3000
    })
    
    if 'error' in compare_result:
        print(f"Error: {compare_result['error']}")
        return
    
    context = compare_result['result']['context']
    
    # Print the first 500 characters of the comparison
    print("\nComparison Preview:")
    print("-" * 50)
    print(context[:500] + "...\n")
    
    print(f"Generated {len(context)} characters of comparison context")
    
    # Example of using this in an AI prompt
    prompt = f"""
You are an expert on municipal development codes.
Compare the following municipal codes and explain the key differences
in their approach to parking requirements for commercial buildings.

{context}

ANALYSIS:
"""
    
    print("\nExample AI Prompt:")
    print("-" * 50)
    print(prompt[:200] + "...\n")

async def example_search():
    """Example searching for content"""
    
    client = MCPClient()
    
    # Get available jurisdictions
    jurisdictions_result = await client.request('get_jurisdictions')
    
    if 'error' in jurisdictions_result:
        print(f"Error: {jurisdictions_result['error']}")
        return
    
    jurisdictions = jurisdictions_result['result']['jurisdictions']
    print(f"Available jurisdictions: {list(jurisdictions.keys())}")
    
    # Search for content
    print("\nSearching for 'zoning' in Gresham...")
    search_result = await client.request('search', {
        'query': 'zoning',
        'jurisdiction': 'Oregon/gresham',
        'limit': 3
    })
    
    if 'error' in search_result:
        print(f"Error: {search_result['error']}")
        return
    
    results = search_result['result']
    print(f"Found {len(results)} results")
    
    if results:
        print("\nFirst result preview:")
        print("-" * 50)
        result = results[0]
        print(f"ID: {result['id']}")
        print(f"Type: {result['chunk_type']}")
        print(f"Document: {result['metadata'].get('document_id', 'Unknown')}")
        print(f"Content: {result['content'][:150]}...")

async def main():
    parser = argparse.ArgumentParser(description='MCP Client Example')
    parser.add_argument('--mode', choices=['search', 'compare'], default='search',
                        help='Example mode (search or compare)')
    
    args = parser.parse_args()
    
    if args.mode == 'search':
        await example_search()
    else:
        await example_jurisdiction_comparison()

if __name__ == "__main__":
    asyncio.run(main())
