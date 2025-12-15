# PostgreSQL MCP Server Integration

Alternative approach: Use Model Context Protocol (MCP) server for direct Claude Desktop integration.

---

## 🤔 What is MCP?

**Model Context Protocol (MCP)** is Anthropic's standard for connecting LLMs to external data sources and tools.

**Traditional approach (our current app):**
```
User → Web App → Python → LLM API → SQL → PostgreSQL
```

**MCP approach:**
```
User → Claude Desktop → MCP Server → PostgreSQL
```

**When to use MCP:**
- Direct Claude Desktop access
- No web app needed
- Ad-hoc queries from Claude interface
- Developer workflow integration

**When to use Web App (our approach):**
- Share with non-technical users (Ivo)
- Custom UI/branding
- Export features
- Access control
- Mobile access

---

## 🛠️ MCP Server Setup (Optional)

### 1. Install PostgreSQL MCP Server

```bash
# Install Node.js if not present
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install PostgreSQL MCP server globally
npm install -g @modelcontextprotocol/server-postgres
```

### 2. Configure Claude Desktop

**On macOS:**
```bash
# Edit Claude config
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**On Windows:**
```powershell
# Edit: %APPDATA%\Claude\claude_desktop_config.json
```

**Add MCP server config:**
```json
{
  "mcpServers": {
    "storesace-postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://storesace:storesace_dev@localhost:5432/storesace"
      ]
    }
  }
}
```

### 3. Restart Claude Desktop

The MCP server will now be available in Claude Desktop.

---

## 💬 Using MCP in Claude Desktop

**Example conversation:**

```
You: I have a retail database connected via MCP.
     Show me today's sales by store.

Claude: I'll query the database for you.
        [Uses MCP to execute SQL]

Results:
- Braga: €2,340.50
- Fafe: €1,890.30
- ...
```

Claude can:
- Inspect schema automatically
- Generate and execute SQL
- Analyze results
- Create follow-up queries

---

## 🔒 Security Considerations

### Read-Only Access (Recommended)

Create read-only PostgreSQL user:

```sql
-- Connect as admin
docker exec -it storesace_db psql -U postgres

-- Create read-only user
CREATE USER readonly_mcp WITH PASSWORD 'secure_password_here';

-- Grant permissions
GRANT CONNECT ON DATABASE storesace TO readonly_mcp;
GRANT USAGE ON SCHEMA prod_515383678 TO readonly_mcp;
GRANT SELECT ON ALL TABLES IN SCHEMA prod_515383678 TO readonly_mcp;
ALTER DEFAULT PRIVILEGES IN SCHEMA prod_515383678
    GRANT SELECT ON TABLES TO readonly_mcp;
```

**Update MCP config:**
```json
{
  "mcpServers": {
    "storesace-postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://readonly_mcp:secure_password_here@localhost:5432/storesace?options=-c%20search_path=prod_515383678"
      ]
    }
  }
}
```

---

## 🆚 Comparison: Web App vs MCP

| Feature | Web App (Streamlit) | MCP + Claude Desktop |
|---------|---------------------|----------------------|
| **Access** | Anyone with URL | Only you (Claude Desktop) |
| **UI** | Custom, branded | Claude's interface |
| **Share** | Easy (send link) | Hard (each person needs setup) |
| **Mobile** | Yes | No (desktop only) |
| **Customization** | Full control | Limited to Claude's UI |
| **Setup** | Medium (server) | Easy (one config file) |
| **Cost** | Hosting + API | Just API (Claude Pro) |
| **Authentication** | Can add | None (local access) |
| **Export** | CSV, PDF, etc. | Copy/paste |
| **Charts** | Built-in | Manual |

---

## 🎯 Recommended Hybrid Approach

**Use both for different purposes:**

### For Ivo (Non-Technical User)
→ **Web App (Streamlit)**
- Easy access via URL
- No setup required
- Custom UI with export features
- Mobile-friendly

### For You (Developer)
→ **MCP + Claude Desktop**
- Quick database exploration
- Ad-hoc analysis
- Development queries
- Schema inspection

---

## 📝 Advanced: Custom MCP Server

Create your own MCP server with business logic:

```javascript
// storesace-mcp-server.js
import { MCPServer } from '@modelcontextprotocol/sdk';
import pg from 'pg';

const server = new MCPServer({
  name: 'storesace',
  version: '1.0.0'
});

// Custom tool: Get sales summary
server.addTool({
  name: 'get_sales_summary',
  description: 'Get sales summary with YoY comparison',
  parameters: {
    type: 'object',
    properties: {
      date: { type: 'string', description: 'Date (YYYY-MM-DD)' }
    }
  },
  async handler({ date }) {
    const client = new pg.Client({
      connectionString: process.env.DATABASE_URL
    });

    await client.connect();

    const result = await client.query(`
      SET search_path TO prod_515383678;
      SELECT
        s.name,
        d.total_net as today_sales,
        -- ... complex YoY logic
      FROM da_stores_date d
      JOIN stores s ON s.id = d.store_id
      WHERE d.date = $1
    `, [date]);

    await client.end();
    return result.rows;
  }
});

server.listen(3000);
```

**Benefits:**
- Encapsulate complex queries
- Add business logic
- Consistent calculations
- Easier for LLM to use

---

## 🔗 Resources

- [PostgreSQL MCP Server - Official](https://www.npmjs.com/package/@modelcontextprotocol/server-postgres)
- [MCP Documentation](https://modelcontextprotocol.io)
- [Postgres MCP Pro (Advanced)](https://github.com/crystaldba/postgres-mcp)
- [Azure PostgreSQL MCP](https://techcommunity.microsoft.com/blog/adforpostgresql/introducing-model-context-protocol-mcp-server-for-azure-database-for-postgresql-/4404360)

---

## 🎬 Conclusion

**For this project:**
- ✅ **Web App** is the primary solution (for Ivo)
- ℹ️ **MCP** is optional (for your own use)

**When to add MCP:**
- You want quick database access in Claude Desktop
- Development/debugging workflow
- Personal analysis tool
- Not a replacement for the web app

**Keep it simple:** Focus on web app first, add MCP later if needed.
