// Operator-provided C# 5 plumbing. Qwen implements only GetOrAdd and TryResolve.
using System;
using System.Collections.Generic;
using System.Globalization;
namespace Smelter.EntityIdentity {
 public sealed class EntityRegistry<T> where T : class {
  private sealed class Entry { public string Id = null; public string Key = null; public T Entity = null; public bool Owned = false; }
  private readonly Func<T, bool> _valid;
  private readonly Func<T, string> _fingerprint;
  private readonly int _capacity;
  private readonly Dictionary<string, Entry> _byId = new Dictionary<string, Entry>(StringComparer.Ordinal);
  private readonly Dictionary<string, Entry> _byKey = new Dictionary<string, Entry>(StringComparer.Ordinal);
  private readonly string _prefix = Guid.NewGuid().ToString("N");
  private long _next;
  public EntityRegistry(Func<T, bool> valid, Func<T, string> fingerprint, int capacity = 256) {
   if (valid == null) throw new ArgumentNullException("valid");
   if (fingerprint == null) throw new ArgumentNullException("fingerprint");
   if (capacity < 1 || capacity > 4096) throw new ArgumentOutOfRangeException("capacity");
   _valid = valid; _fingerprint = fingerprint; _capacity = capacity;
  }
  public int Count { get { return _byId.Count; } }
  private bool Validate(T entity, out string key, out string reason) {
   key = null; reason = null;
   try {
    if (entity == null || !_valid(entity)) { reason = "entity_invalid"; return false; }
    key = _fingerprint(entity);
    if (String.IsNullOrWhiteSpace(key) || key.Length > 256) { reason = "invalid_fingerprint"; return false; }
    return true;
   } catch (Exception error) { key = null; reason = "validation_error:" + error.Message; return false; }
  }
  private void Remove(Entry entry) {
   _byId.Remove(entry.Id); Entry indexed;
   if (_byKey.TryGetValue(entry.Key, out indexed) && Object.ReferenceEquals(indexed, entry)) _byKey.Remove(entry.Key);
  }
  private string NextId(out string reason) {
   reason = null;
   if (_next == Int64.MaxValue) { reason = "id_space_exhausted"; return null; }
   _next++; return _prefix + "-" + _next.ToString(CultureInfo.InvariantCulture);
  }
  public string Observe(T entity, out string reason) { return GetOrAdd(entity, false, out reason); }
  public string RegisterOwned(T entity, out string reason) { return GetOrAdd(entity, true, out reason); }
  private string GetOrAdd(T entity, bool owned, out string reason) {
   string key = null;
   if (!Validate(entity, out key, out reason)) return null;
   Entry eByKey; T current; string fp;
   if (_byKey.TryGetValue(key, out eByKey)) {
    current = eByKey.Entity;
    try {
     if (current != null && _valid(current)) {
      fp = _fingerprint(current);
      if (fp == eByKey.Key) {
       eByKey.Entity = entity;
       if (owned) eByKey.Owned = true;
       reason = null; return eByKey.Id;
      }
     }
    } catch (Exception) { }
    Remove(eByKey);
   }
   if (_byId.Count >= _capacity) { reason = "capacity_reached"; return null; }
   string newId = NextId(out reason);
   if (reason != null) return null;
   Entry newEntry = new Entry();
   newEntry.Id = newId;
   newEntry.Key = key;
   newEntry.Entity = entity;
   newEntry.Owned = owned;
   _byId[newId] = newEntry;
   _byKey[key] = newEntry;
   reason = null; return newId;
  }
  public bool TryResolve(string id, bool requireOwned, out T entity, out string reason) {
   entity = null; reason = null;
   if (String.IsNullOrEmpty(id)) { reason = "invalid_id"; return false; }
   Entry entryById;
   if (!_byId.TryGetValue(id, out entryById)) { reason = "unknown_id"; return false; }
   string currentKey = null; string errReason = null;
   if (!Validate(entryById.Entity, out currentKey, out errReason)) { Remove(entryById); reason = errReason; return false; }
   if (currentKey != entryById.Key) { Remove(entryById); reason = "identity_changed"; return false; }
   if (requireOwned && !entryById.Owned) { reason = "not_owned"; return false; }
   entity = entryById.Entity; reason = null; return true;
  }
  public bool Retire(string id, out string reason) {
   reason = null;
   if (String.IsNullOrEmpty(id)) { reason = "invalid_id"; return false; }
   Entry entry; if (!_byId.TryGetValue(id, out entry)) { reason = "unknown_id"; return false; }
   Remove(entry); return true;
  }
  public void Clear() { _byId.Clear(); _byKey.Clear(); }
 }
}