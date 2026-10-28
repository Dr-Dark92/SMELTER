"""Compact schema errors without echoing rejected code; uses the MCP SDK dependency."""


def validate(arguments, schema, name):
    from jsonschema.validators import validator_for
    error = next(validator_for(schema)(schema).iter_errors(arguments), None)
    if error is None:
        return None
    location = '.'.join(str(p)[:80] for p in list(error.absolute_path)[:8]) or 'arguments'
    result = {'status':'error', 'code':'input_contract_error',
              'error':'Arguments violate the advertised schema at '+location+' ('+str(error.validator)+'). No operation executed.',
              'required_arguments':schema.get('required',[])[:24],
              'expected_types':{k:v.get('type','object') for k,v in list(schema.get('properties',{}).items())[:24]},
              'next_action':'Correct the argument shape using the supplied tool schema. Do not JSON-encode arrays or switch to shell/edit.'}
    if name in ('propose_coding_edits','propose_coding_patch','propose_coding_edit'):
        result.update(recommended_tool='propose_coding_edit',
                      call_shape={'workspace_id':'existing workspace ID','relative_path':'exact project-relative path',
                                  'expected_sha256':'SHA256 returned by read_coding_file','old_text':'exact existing text','new_text':'replacement text'})
    return result
