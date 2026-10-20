/* Operator configuration and per-message MCP selection. Never render server HTML. */
const SmelterMcp = (() => {
  function mount(right, folder, permissionsBox, request, getGrants) {
    const transport = document.createElement('input'); transport.type = 'checkbox'; transport.id = 'mcpTransport';
    const transportLabel = document.createElement('label'); transportLabel.append(transport, document.createTextNode(' Route built-in tools through MCP for the next message'));
    const external = document.createElement('div'); external.id = 'mcpToolGrants';
    const selected = [];
    permissionsBox.append(document.createElement('br'), transportLabel, external);
    const button = document.createElement('button'); button.className = 'navbtn'; button.textContent = 'MCP Connections';
    const panel = document.createElement('section'); panel.className = 'panel'; panel.id = 'mcpPanel';
    const heading = document.createElement('h3'); heading.textContent = 'MCP Connections';
    const info = document.createElement('p'); info.setAttribute('role', 'status');
    const note = document.createElement('p'); note.textContent = 'Local stdio servers run as your OS user. Tool selection is not an OS sandbox. Saving does not start a server; discovery does. Connections close after each discovery or call.';
    const install = document.createElement('code'); install.textContent = 'python -m pip install -r tools/dashboard/requirements-mcp.txt';
    const editor = document.createElement('textarea'); editor.rows = 12; editor.style.cssText = 'width:100%;box-sizing:border-box'; editor.setAttribute('aria-label', 'MCP server configuration');
    const save = document.createElement('button'); save.textContent = 'Save MCP configuration';
    const refresh = document.createElement('button'); refresh.textContent = 'Refresh MCP status';
    const choose = document.createElement('select'); choose.setAttribute('aria-label', 'MCP server');
    const probe = document.createElement('button'); probe.textContent = 'Start server and discover tools';
    const details = document.createElement('div');
    panel.append(heading, info, note, install, editor, save, refresh, choose, probe, details);
    function clearSelections() { selected.length = 0; external.replaceChildren(); }
    async function load() {
      try {
        const data = await request('/api/mcp/status');
        info.textContent = 'SDK: ' + data.sdk.status + ' · required ' + data.sdk.required_version + ' · stdio · no persistent server';
        editor.value = JSON.stringify(data.config, null, 2); choose.replaceChildren();
        for (const sid of ['smelter', ...data.config.servers.filter(x => x.enabled).map(x => x.id)]) {
          const option = document.createElement('option'); option.value = sid; option.textContent = sid; choose.append(option);
        }
        probe.disabled = data.sdk.status !== 'installed';
      } catch (error) { info.textContent = error.message; }
    }
    button.onclick = () => {
      right.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
      right.querySelectorAll('.navbtn').forEach(x => x.classList.remove('active'));
      panel.classList.add('active'); button.classList.add('active'); load();
    };
    refresh.onclick = load;
    save.onclick = async () => {
      save.disabled = true;
      try {
        const config = JSON.parse(editor.value);
        await request('/api/mcp', 'POST', {action: 'save', config});
        clearSelections(); details.replaceChildren(); await load(); info.textContent += ' · Configuration saved; no server started.';
      } catch (error) { info.textContent = error.message; }
      finally { save.disabled = false; }
    };
    probe.onclick = async () => {
      probe.disabled = true; info.textContent = 'Starting selected local server for discovery…';
      try {
        const sid = choose.value;
        const result = await request('/api/mcp', 'POST', {action: 'probe', server: sid, permissions: sid === 'smelter' ? getGrants() : {}});
        details.replaceChildren(); info.textContent = result.server + ': connected · protocol ' + result.protocol_version + ' · ' + result.tools.length + ' tools discovered · process closed';
        for (const tool of result.tools) {
          const line = document.createElement('p'); line.textContent = tool.name + (tool.allowed ? ' · allowlisted' : ' · blocked by configuration');
          const description = document.createElement('small'); description.textContent = tool.description; details.append(line, description);
          if (sid !== 'smelter' && tool.allowed && !selected.some(x => x.server === sid && x.name === tool.name)) {
            const checkbox = document.createElement('input'); checkbox.type = 'checkbox';
            const label = document.createElement('label'); label.style.display = 'block';
            label.append(checkbox, document.createTextNode(' Allow ' + sid + '/' + tool.name + ' for the next message (server OS access)'));
            external.append(label); selected.push({server: sid, name: tool.name, checkbox});
          }
        }
        if (!result.tools.length) details.textContent = 'No tools exposed. For smelter, select the built-in permissions above before discovery.';
      } catch (error) { info.textContent = error.message; }
      finally { probe.disabled = false; }
    };
    (folder?.querySelector('.config-folder-items') || right).prepend(button, panel);
    return {collect() {
      const result = {transport: transport.checked ? 'mcp' : 'python',
        mcp_tools: selected.filter(x => x.checkbox.checked).map(x => ({server: x.server, name: x.name}))};
      transport.checked = false; selected.forEach(x => { x.checkbox.checked = false; }); return result;
    }};
  }
  return {mount};
})();
