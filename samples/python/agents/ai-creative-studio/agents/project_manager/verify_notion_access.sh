#!/bin/bash
# Quick verification that Notion database is accessible

source ../../.env

echo "🔍 Verifying Notion Database Access..."
echo "Database ID: $NOTION_DATABASE_ID"
echo ""

# Try to retrieve the database
RESPONSE=$(curl -s -X GET "https://api.notion.com/v1/databases/$NOTION_DATABASE_ID" \
    -H "Authorization: Bearer $NOTION_API_KEY" \
    -H 'Notion-Version: 2022-06-28')

# Check if we got an error
if echo "$RESPONSE" | grep -q '"object":"error"'; then
    echo "❌ Database access FAILED"
    echo "$RESPONSE" | grep -o '"message":"[^"]*"'
    echo ""
    echo "Action needed:"
    echo "1. Open your Notion database"
    echo "2. Click '...' menu → 'Connections'"
    echo "3. Add 'devfest_ahlen_project_mcp' integration"
    exit 1
else
    echo "✅ Database access SUCCESSFUL!"
    echo ""
    echo "Database details:"
    echo "$RESPONSE" | grep -o '"title":\[{"type":"text","text":{"content":"[^"]*"' | head -1
    echo ""
    echo "✨ The Project Manager agent should now be able to create pages in Notion!"
    exit 0
fi
