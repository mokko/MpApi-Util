from MpApi.Utils.becky.update_caches import query_persons
from MpApi.Utils.Ria import RIA, init_ria


def test_query_persons() -> None:
    c = init_ria()
    name = "Eduard Schmidt"
    date = "1892"
    r = query_persons(name=name, date=date, client=c)
    assert r == [3347]
    # print(f"{r}") # should be a list with objIds
