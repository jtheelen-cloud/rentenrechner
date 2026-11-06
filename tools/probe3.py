import json,urllib.request
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}),timeout=40); return r.read().decode("utf8","ignore")
    except Exception as e: return "ERR "+str(e)
O="https://de.openlegaldata.io/api"
res={}
for u in [O+"/law_books/?code=BGB", O+"/law_books/?slug=bgb&limit=3", O+"/law_books/?search=ArbGG&limit=3", O+"/laws/56326/", O+"/laws/search/?text=Arbeitsgerichtsgesetz", O+"/law_books/?limit=2"]:
    res[u]=get(u)[:1500]
json.dump(res,open("tools/probe3.json","w"),ensure_ascii=False,indent=1)
