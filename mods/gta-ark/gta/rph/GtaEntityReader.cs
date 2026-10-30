// First native-provider slice: read boundary only
// Operator supplied EntityRegistry<T>, EntitySnapshot. This file does not spawn/command/schedule/fail into runtime.
using System;
using Smelter.EntityIdentity;
namespace Smelter.Gta
{
    public sealed class GtaEntityReader
    {
        private readonly Func<string> _runtimeGate;
        private readonly long _managedThreadId;
        private readonly EntityRegistry<Rage.Entity> _registry;

        public GtaEntityReader(Func<string> runtimeGate, int capacity = 256)
        {
            if (runtimeGate == null) throw new System.ArgumentNullException("runtimeGate");
            _runtimeGate = runtimeGate;
            _managedThreadId = System.Threading.Thread.CurrentThread.ManagedThreadId;

            var valid = new System.Func<Rage.Entity, bool>(e => e != null && e.IsValid() && e.Handle.Value != 0);
            var fp = new System.Func<Rage.Entity, string>(
                e => e.Handle.Value.ToString() + "@" + e.MemoryAddress.ToString());
            _registry = new EntityRegistry<Rage.Entity>(valid, fp, capacity);
        }

        private bool RejectOtherThread(out string reason)
        {
            reason = null;
            if (System.Threading.Thread.CurrentThread.ManagedThreadId != _managedThreadId)
            {
                reason = "wrong_game_thread";
                return true;
            }
            return false;
        }

        private bool TryGate(out string reason)
        {
            reason = null;
            try
            {
                string result = _runtimeGate();
                if (result == null) return true;
                reason = result.Length == 0 ? "runtime_gate_invalid" : result;
                return false;
            }
            catch (Exception error)
            {
                reason = "runtime_gate_error:" + error.Message;
                return false;
            }
        }

        public string Observe(Rage.Entity entity, out string reason)
        {
            reason = null;
            if (RejectOtherThread(out reason))
                return null;

            if (!TryGate(out reason))
                return null;

            reason = null;
            return _registry.Observe(entity, out reason);
        }

        public bool TryRead(string id, out EntitySnapshot snapshot, out string reason)
        {
            snapshot = null;
            reason = null;
            if (RejectOtherThread(out reason))
                return false;

            if (!TryGate(out reason))
                return false;

            Rage.Entity candidate;
            if (!_registry.TryResolve(id, false, out candidate, out reason))
                return false;

            try
            {
                if (candidate == null || !candidate.IsValid() || candidate.Handle.Value == 0)
                {
                    reason = "entity_invalid";
                    return false;
                }
            }
            catch (System.Exception e)
            {
                reason = "native_read_error:" + e.Message;
                return false;
            }

            EntitySnapshot localSnapshot = new EntitySnapshot();
            localSnapshot.Id = id;
            try
            {
                Rage.Ped pedRef = candidate as Rage.Ped;
                if (pedRef != null)
                {
                    localSnapshot.Kind = "character";
                    localSnapshot.Human = pedRef.IsHuman;
                    localSnapshot.Player = pedRef.IsPlayer;
                }
                else
                {
                    var vehRef = candidate as Rage.Vehicle;
                    if (vehRef != null)
                    {
                        localSnapshot.Kind = "vehicle";
                        localSnapshot.Human = false;
                        localSnapshot.Player = false;
                    }
                    else
                    {
                        reason = "unsupported_entity_kind";
                        return false;
                    }
                }
            }
            catch (System.Exception e)
            {
                reason = "native_read_error:" + e.Message;
                return false;
            }

            Rage.Vector3 localPos;
            try
            {
                localPos = candidate.Position;
                double x = localPos.X, y = localPos.Y, z = localPos.Z;
                if (Double.IsNaN(x) || Double.IsInfinity(x) || Double.IsNaN(y) || Double.IsInfinity(y) || Double.IsNaN(z) || Double.IsInfinity(z))
                {
                    reason = "nonfinite_position";
                    return false;
                }
                localSnapshot.X = x;
                localSnapshot.Y = y;
                localSnapshot.Z = z;
            }
            catch (System.Exception e)
            {
                reason = "native_read_error:" + e.Message;
                return false;
            }

            try
            {
                localSnapshot.Alive = !candidate.IsDead;
                localSnapshot.Valid = true;
            }
            catch (System.Exception e)
            {
                reason = "native_read_error:" + e.Message;
                return false;
            }

            if (!_registry.TryResolve(id, false, out candidate, out reason))
                return false;

            snapshot = localSnapshot;
            return true;
        }
    }
}