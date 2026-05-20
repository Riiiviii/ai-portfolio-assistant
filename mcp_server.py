import json
from fastmcp import FastMCP
from pathlib import Path

path = Path(__file__).parent / "resume.json"

with open(path, "r") as f:
    data = json.load(f)


mcp = FastMCP("resume-mcp-server")


@mcp.tool()
def get_profile():
    """Get personal information"""
    return data["profile"]


@mcp.tool()
def get_experience():
    """Get personal work experience"""
    return data["experience"]


@mcp.tool()
def get_technical_skills():
    """Get programming technical skills"""
    return data["skills"]


@mcp.tool()
def get_projects():
    """Get personal projects"""
    return data["projects"]


@mcp.tool()
def get_education():
    """Get education"""
    return data["education"]


@mcp.tool()
def get_socials():
    """Get work socials"""
    return data["socials"]


@mcp.tool()
def get_references():
    """Get work references"""
    return data["references"]


@mcp.tool()
def get_interests():
    """Get personal interests"""
    return data["interests"]


if __name__ == "__main__":
    print("MCP server started")
    mcp.run(transport="sse", host="127.0.0.1", port=8001)
