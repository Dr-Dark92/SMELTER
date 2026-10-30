// Operator-owned pure C# conformance fixture. No game SDK, Lua or native calls.
using System;
using System.Collections.Generic;
using Smelter.EntityIdentity;

public static class EntityRegistryFixture
{
    private sealed class Item { public string Key; public bool Valid=true; public bool ThrowValid, ThrowKey; }
    private static int checks;
    private static void Check(bool value,string name) {
        checks++; if(!value)throw new Exception("REGISTRY FAIL: "+name);
        Console.WriteLine("[REGISTRY PASS] "+name);
    }
    private static EntityRegistry<Item> Registry(int capacity=256) {
        return new EntityRegistry<Item>(delegate(Item e){if(e.ThrowValid)throw new Exception("valid_failed");return e.Valid;},
            delegate(Item e){if(e.ThrowKey)throw new Exception("key_failed");return e.Key;},capacity);
    }
    private static void RejectConstructor(Action action) {
        bool rejected=false;try{action();}catch(ArgumentException){rejected=true;}
        Check(rejected,"constructor rejects invalid dependency/bound");
    }
    public static int Main() {
        try {
            RejectConstructor(delegate{new EntityRegistry<Item>(null,e=>e.Key);});
            RejectConstructor(delegate{new EntityRegistry<Item>(e=>true,null);});
            RejectConstructor(delegate{Registry(0);});RejectConstructor(delegate{Registry(4097);});
            var r=Registry(2);string why;Item resolved;
            var a=new Item{Key="handle-a:g1"};string id=r.Observe(a,out why);
            Check(!String.IsNullOrWhiteSpace(id) && why==null && r.Count==1,"observe returns opaque id");
            Check(id!=a.Key,"id is separate from engine fingerprint");
            Check(r.Observe(new Item{Key=a.Key},out why)==id && r.Count==1,"aliases preserve live identity");
            Check(r.TryResolve(id,false,out resolved,out why) && resolved.Key==a.Key && why==null,"resolve observed entity");
            Check(!r.TryResolve(id,true,out resolved,out why) && resolved==null && why=="not_owned","observation does not grant ownership");
            Check(r.RegisterOwned(a,out why)==id,"explicit registration promotes same identity");
            Check(r.TryResolve(id,true,out resolved,out why),"resolve explicit owned entity");
            r.Observe(a,out why);Check(r.TryResolve(id,true,out resolved,out why),"observation does not drop ownership");
            var b=new Item{Key="handle-b:g1"};string bid=r.Observe(b,out why);
            Check(bid!=id && r.Count==2,"distinct identity");
            Check(r.Observe(new Item{Key="full"},out why)==null && why=="capacity_reached" && r.Count==2,"capacity fails without eviction");
            Check(r.Retire(bid,out why) && r.Count==1 && why==null,"retire removes identity");
            Check(!r.TryResolve(bid,false,out resolved,out why) && why=="unknown_id","retired id cannot resolve");
            string b2=r.Observe(b,out why);Check(b2!=bid,"reobservation never reuses retired id");
            b.Valid=false;Check(!r.TryResolve(b2,false,out resolved,out why) && resolved==null && why=="entity_invalid" && r.Count==1,"liveness failure retires");
            a.Key="handle-a:g2";
            Check(!r.TryResolve(id,true,out resolved,out why) && why=="identity_changed" && r.Count==0,"changed generation invalidates owned id");
            string a2=r.Observe(a,out why);Check(a2!=id,"recycled handle receives fresh id");
            Check(!r.TryResolve(a2,true,out resolved,out why) && why=="not_owned","recycled identity does not inherit ownership");
            Check(r.Observe(null,out why)==null && why=="entity_invalid","null entity rejected");
            Check(r.Observe(new Item{Key=""},out why)==null && why=="invalid_fingerprint","empty fingerprint rejected");
            Check(r.Observe(new Item{Key=new String('x',257)},out why)==null && why=="invalid_fingerprint","oversized fingerprint rejected");
            Check(r.Observe(new Item{Key="bad",ThrowValid=true},out why)==null && why.StartsWith("validation_error:"),"validation exception contained");
            Check(r.Observe(new Item{Key="bad",ThrowKey=true},out why)==null && why.StartsWith("validation_error:"),"fingerprint exception contained");
            a.ThrowValid=true;
            Check(!r.TryResolve(a2,false,out resolved,out why) && why.StartsWith("validation_error:") && r.Count==0,"resolve exception retires stale entry");
            a.ThrowValid=false;string beforeClear=r.RegisterOwned(a,out why);r.Clear();
            Check(r.Count==0 && !r.TryResolve(beforeClear,true,out resolved,out why),"clear invalidates all ids");
            string afterClear=r.Observe(a,out why);
            Check(afterClear!=beforeClear && !r.TryResolve(afterClear,true,out resolved,out why),"clear keeps id freshness and drops ownership");
            Check(afterClear!=id && !r.TryResolve(id,false,out resolved,out why),"clear never reissues even the oldest retired id");
            Check(!r.Retire("unknown",out why) && why=="unknown_id","unknown retirement is explicit");
            Check(!r.TryResolve(null,false,out resolved,out why) && resolved==null && why=="invalid_id","null id rejected");
            Check(!r.Retire("",out why) && why=="invalid_id","empty retirement rejected");
            var isolated=Registry();Check(!isolated.TryResolve(afterClear,false,out resolved,out why) && why=="unknown_id","registries are isolated");
            foreach(string stale in new [] {"dead","changed","valid_throws","key_throws"}) {
                var tight=Registry(1);var old=new Item{Key="reused:g1"};string oldId=tight.RegisterOwned(old,out why);
                if(stale=="dead") old.Valid=false;
                if(stale=="changed") old.Key="different:g2";
                if(stale=="valid_throws") old.ThrowValid=true;
                if(stale=="key_throws") old.ThrowKey=true;
                var fresh=new Item{Key="reused:g1"};string freshId=tight.Observe(fresh,out why);
                Check(freshId!=null && freshId!=oldId && tight.Count==1 && why==null,"stale observation retired before capacity: "+stale);
                Check(!tight.TryResolve(oldId,false,out resolved,out why) && why=="unknown_id","old mapping removed: "+stale);
                Check(!tight.TryResolve(freshId,true,out resolved,out why) && why=="not_owned","stale observation never transfers ownership: "+stale);
            }
            Console.WriteLine("REGISTRY_RESULT|checks="+checks+";failures=0");return 0;
        }catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
