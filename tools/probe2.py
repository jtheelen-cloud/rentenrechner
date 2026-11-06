import json,urllib.request,urllib.parse,sys
B="https://testphase.rechtsinformationen.bund.de"
def get(u,raw=False):
    r=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}),timeout=30)
    d=r.read(); return d if raw else json.loads(d)
out=[]
for slug,kurz,name in json.load(open("tools/probe_list.json")):
    try:
        j=get(B+"/v1/legislation?"+urllib.parse.urlencode({"searchTerm":kurz,"size":5}))
        hits=[(m["item"].get("name"),m["item"].get("abbreviation") or m["item"].get("alternateName"),m["item"]["@id"]) for m in j.get("member",[])]
        out.append({"slug":slug,"kurz":kurz,"total":j.get("totalItems"),"hits":hits})
    except Exception as e: out.append({"slug":slug,"err":str(e)})
res={"search":out}
try:
    j=get(B+"/v1/legislation?searchTerm=Betriebsverfassungsgesetz&size=1")
    iid=j["member"][0]["item"]["@id"]; res["item_list"]=j["member"][0]
    res["item"]=get(B+iid)
except Exception as e: res["itemerr"]=str(e)
for p in ["/v3/api-docs","/v1/openapi.json","/api/v1/openapi.json","/openapi.json"]:
    try: d=get(B+p,raw=True); res["openapi_"+p]=d[:200].decode("utf8","ignore"); open("tools/openapi.json","wb").write(d); break
    except Exception as e: res["openapi_"+p]=str(e)
json.dump(res,open("tools/probe2.json","w"),ensure_ascii=False,indent=1)
