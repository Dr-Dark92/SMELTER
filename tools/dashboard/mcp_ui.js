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
    const discoveryStatus = document.createElement('p'); discoveryStatus.id='mcpDiscoveryStatus'; discoveryStatus.textContent='Last discovery: not tested in this page session.';
    const approvals = document.createElement('p'); approvals.id='mcpApprovals';
    let discoverySnapshot = null;
    const note = document.createElement('p'); note.textContent = 'Local stdio servers run as your OS user. Tool selection is not an OS sandbox. Saving does not start a server; discovery does. Connections close after each discovery or call.';
    const install = document.createElement('code'); install.textContent = 'python -m pip install -r tools/dashboard/requirements-mcp.txt';
    const editor = document.createElement('textarea'); editor.rows = 12; editor.style.cssText = 'width:100%;box-sizing:border-box'; editor.setAttribute('aria-label', 'MCP server configuration');
    const save = document.createElement('button'); save.textContent = 'Save MCP configuration';
    const refresh = document.createElement('button'); refresh.textContent = 'Refresh MCP status';
    const choose = document.createElement('select'); choose.setAttribute('aria-label', 'MCP server');
    const probe = document.createElement('button'); probe.textContent = 'Start server and discover tools';
    const details = document.createElement('div');
    panel.append(heading, info, discoveryStatus, approvals, note, install, editor, save, refresh, choose, probe, details);
    function refreshApprovals() {
      const grants=getGrants(), names=[];
      if(grants.inventory_root)names.push('inventory_directory');
      if(grants.write_diagnostics)names.push('write_diagnostic_markdown');
      if(grants.rea_analysis)names.push('rea_capabilities','rea_inspect_pe_resources');
      if(grants.model_ids?.length)names.push('inspect_model_attachment ('+grants.model_ids.length+' attachments)');
      const extra=selected.filter(x=>x.checkbox.checked).map(x=>x.server+'/'+x.name);
      approvals.textContent='Next-message built-in selection: '+(names.join(', ')||'none')+' · transport: '+(transport.checked?'MCP':'direct Python')+' · external MCP selection: '+(extra.join(', ')||'none');
      if(discoverySnapshot && discoverySnapshot.server==='smelter' && JSON.stringify(grants)!==discoverySnapshot.grants)discoveryStatus.textContent=discoverySnapshot.text+' · Permissions changed since discovery; discovery is a historical snapshot.';
      else if(discoverySnapshot)discoveryStatus.textContent=discoverySnapshot.text;
    }
    permissionsBox.addEventListener('change',refreshApprovals);
    function clearSelections() { selected.length = 0; external.replaceChildren(); }
    async function load() {
      try {
        const data = await request('/api/mcp/status');
        info.textContent = 'SDK: ' + data.sdk.status + ' · required ' + data.sdk.required_version + ' · stdio · no persistent server';
        editor.value = JSON.stringify(data.config, null, 2); choose.replaceChildren();
        for (const sid of ['smelter', ...data.config.servers.filter(x => x.enabled).map(x => x.id)]) {
          const option = document.createElement('option'); option.value = sid; option.textContent = sid; choose.append(option);
        }
        probe.disabled = data.sdk.status !== 'installed';refreshApprovals();
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
        clearSelections(); details.replaceChildren(); discoverySnapshot=null;discoveryStatus.textContent='Configuration changed. Discover again to verify the selected server.';await load(); info.textContent += ' · Configuration saved; no server started.';
      } catch (error) { info.textContent = error.message; }
      finally { save.disabled = false; }
    };
    probe.onclick = async () => {
      probe.disabled = true; discoveryStatus.textContent = 'Starting selected local server for discovery…';
      try {
        const sid = choose.value;const granted=sid==='smelter'?getGrants():{};
        const result = await request('/api/mcp', 'POST', {action: 'probe', server: sid, permissions: granted});
        details.replaceChildren(); const text='Last discovery: '+result.server+' · '+new Date().toLocaleTimeString()+' · protocol '+result.protocol_version+' · '+result.tools.length+' tools discovered · process closed';discoverySnapshot={server:sid,grants:JSON.stringify(granted),text};discoveryStatus.textContent=text;
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
        if (!result.tools.length) details.textContent = 'This discovery had no approved built-in tools. Select permissions in chat, then discover again. Enabled skills alone do not grant tools.';
      } catch (error) { discoverySnapshot=null;discoveryStatus.textContent='Discovery failed: '+error.message; }
      finally { probe.disabled = false;refreshApprovals(); }
    };
    (folder?.querySelector('.config-folder-items') || right).prepend(button, panel);
    refreshApprovals();
    return {refreshApprovals,collect() {
      const result = {transport: transport.checked ? 'mcp' : 'python',
        mcp_tools: selected.filter(x => x.checkbox.checked).map(x => ({server: x.server, name: x.name}))};
      transport.checked = false; selected.forEach(x => { x.checkbox.checked = false; }); return result;
    }};
  }
  return {mount};
})();
