import json,urllib.request
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}),timeout=40); return r.read().decode("utf8","ignore")
    except Exception as e: return "ERR "+str(e)
O="https://de.openlegaldata.io/api"
res={}
for u in [O+"/lawbooks/?code=BGB", O+"/lawbooks/?slug=bgb", O+"/lawbooks/?search=ArbGG", O+"/laws/?book__code=BGB&limit=2",
          O+"/laws/?book_slug=bgb&limit=2", O+"/laws/?search=Arbeitsgerichtsgesetz&limit=2", O+"/", O+"/laws/?book=1&limit=1"]:
    res[u]=get(u)[:1500]
json.dump(res,open("tools/probe3.json","w"),ensure_ascii=False,indent=1)
