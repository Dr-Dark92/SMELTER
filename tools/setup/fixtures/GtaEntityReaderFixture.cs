// Operator-owned fake SDK fixture. These types never enter a game/plugin build.
using System;
using System.Threading;
using Smelter.EntityIdentity;
using Smelter.Gta;
namespace Rage {
 public struct PoolHandle { public uint Value; }
 public struct Vector3 { public float X,Y,Z; }
 public class Entity {
  public int Reads; public bool Live=true, Dead, ThrowRead, ThrowPosition; public uint Key=258;
  public IntPtr Address=new IntPtr(100); public Vector3 Point=new Vector3 {X=1,Y=2,Z=3};
  public Action AfterPosition;
  protected void Touch(){Reads++;if(ThrowRead)throw new Exception("read_failed");}
  public bool IsValid(){Touch();return Live;}
  public PoolHandle Handle {get{Touch();return new PoolHandle {Value=Key};}}
  public IntPtr MemoryAddress {get{Touch();return Address;}}
  public bool IsDead {get{Touch();return Dead;}}
  public Vector3 Position {get{Touch();if(ThrowPosition)throw new Exception("position_failed");if(AfterPosition!=null)AfterPosition();return Point;}}
 }
 public class Ped:Entity {
  public bool Human=true,Player;
  public bool IsHuman {get{Touch();return Human;}}
  public bool IsPlayer {get{Touch();return Player;}}
 }
 public class Vehicle:Entity {}
}
public static class GtaEntityReaderFixture {
 static int checks;
 static void Check(bool ok,string message){checks++;if(!ok)throw new Exception("READER FAIL: "+message);Console.WriteLine("[READER PASS] "+message);}
 public static int Main(){try{
  string why;EntitySnapshot data;
  bool rejected=false;try{new GtaEntityReader(null);}catch(ArgumentException){rejected=true;}
  Check(rejected,"null gate rejected");
  rejected=false;try{new GtaEntityReader(()=>null,0);}catch(ArgumentException){rejected=true;}
  Check(rejected,"invalid capacity rejected");
  int calls=0;string gate=null;bool gateThrows=false;
  var r=new GtaEntityReader(delegate{calls++;if(gateThrows)throw new Exception("gate_fault");return gate;},2);
  Check(calls==0,"construction passive");
  var human=new Rage.Ped {Player=true};
  gate="network_session_active";
  Check(r.Observe(human,out why)==null && why==gate && human.Reads==0,"refused observation touches no SDK");
  Check(!r.TryRead("unknown",out data,out why) && data==null && why==gate && human.Reads==0,"refused read touches no SDK");
  gate="";Check(r.Observe(human,out why)==null && why=="runtime_gate_invalid" && human.Reads==0,"empty gate fails closed");
  gateThrows=true;Check(r.Observe(human,out why)==null && why.StartsWith("runtime_gate_error:") && human.Reads==0,"throwing gate contained");
  Check(!r.TryRead("unknown",out data,out why) && data==null && why.StartsWith("runtime_gate_error:") && human.Reads==0,"throwing read gate contained before SDK");
  gateThrows=false;gate=null;
  int beforeObserve=calls;
  string id=r.Observe(human,out why);Check(id!=null && why==null,"observe human");
  Check(calls==beforeObserve+1,"observation invokes runtime gate once");
  int beforeCapture=calls;
  Check(r.TryRead(id,out data,out why) && why==null && data.Id==id && data.Kind=="character" && data.Valid && data.Alive && data.Human && data.Player && data.X==1 && data.Y==2 && data.Z==3,"complete player snapshot");
  Check(calls==beforeCapture+1,"capture invokes runtime gate once");
  var npc=new Rage.Ped {Key=259};string npcId=r.Observe(npc,out why);
  Check(npcId!=id && r.TryRead(npcId,out data,out why) && data.Human && !data.Player,"full handle counter distinguishes same pool index");
  Check(r.Observe(new Rage.Vehicle {Key=400},out why)==null && why=="capacity_reached","reader capacity bounded");
  npc.Dead=true;Check(r.TryRead(npcId,out data,out why) && !data.Alive,"death represented truthfully");
  human.Key=514;Check(!r.TryRead(id,out data,out why) && data==null && why=="identity_changed","generation change invalidates old id");
  string fresh=r.Observe(human,out why);Check(fresh!=null && fresh!=id,"recycled entity gets fresh id");
  npc.Live=false;Check(!r.TryRead(npcId,out data,out why) && data==null && why=="entity_invalid","despawn rejected");
  var vehicle=new Rage.Vehicle {Key=400};string vid=r.Observe(vehicle,out why);
  Check(r.TryRead(vid,out data,out why) && data.Kind=="vehicle" && !data.Human && !data.Player,"vehicle never fabricated as human");
  vehicle.Dead=true;Check(r.TryRead(vid,out data,out why) && !data.Alive,"vehicle death represented truthfully");
  vehicle.Point.X=float.NaN;Check(!r.TryRead(vid,out data,out why) && data==null && why=="nonfinite_position","NaN rejected");
  vehicle.Point.X=float.PositiveInfinity;Check(!r.TryRead(vid,out data,out why) && data==null && why=="nonfinite_position","infinity rejected");
  vehicle.Point.X=1;vehicle.ThrowPosition=true;Check(!r.TryRead(vid,out data,out why) && data==null && why.StartsWith("native_read_error:"),"position read exception contained");
  vehicle.ThrowPosition=false;vehicle.ThrowRead=true;Check(!r.TryRead(vid,out data,out why) && data==null && why!=null,"SDK exception contained");
  Check(!r.TryRead("unknown",out data,out why) && data==null && why=="unknown_id","unknown id rejected");
  int before=human.Reads,gateBefore=calls;bool foreignSuccess=true;string foreignReason=null;EntitySnapshot foreignData=null;
  var thread=new Thread(delegate(){foreignSuccess=r.TryRead(fresh,out foreignData,out foreignReason);});thread.Start();
  Check(thread.Join(2000),"foreign thread completes within bound");
  Check(!foreignSuccess && foreignData==null && foreignReason=="wrong_game_thread" && human.Reads==before && calls==gateBefore,"foreign thread rejects before gate or SDK");
  var unsupported=new GtaEntityReader(()=>null);string oid=unsupported.Observe(new Rage.Entity(),out why);
  Check(oid!=null && !unsupported.TryRead(oid,out data,out why) && data==null && why=="unsupported_entity_kind","unsupported type rejects explicitly");
  Check(unsupported.Observe(new Rage.Ped {Live=false},out why)==null && why=="entity_invalid","invalid entity rejected on observation");
  Check(unsupported.Observe(new Rage.Ped {Key=0},out why)==null && why=="entity_invalid","zero handle rejected on observation");
  var unstable=new Rage.Ped();var changing=new GtaEntityReader(()=>null);string changingId=changing.Observe(unstable,out why);
  unstable.AfterPosition=delegate{unstable.Key++;};
  Check(!changing.TryRead(changingId,out data,out why) && data==null && why=="identity_changed","capture revalidates after reads");
  Console.WriteLine("READER_RESULT|checks="+checks+";failures=0");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
