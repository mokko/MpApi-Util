"""

WORK IN PROGRESS

For all object items in a group
connect a reference to a Multimedia/asset record
set standardbild

Do we have to check if reference already exists? We should, but dont need to
We need
- objId and mulId
- get Multimedia record, change it, upload it again
- set standardbild

ObjId comes from group. How do we find the corresponding Assets?
VIII A 23050 (103) in dateiname

"""

#
# AssetUploader.py
# there is a record in memory and we change it before we create it
r = Record(templateM)
r.add_reference(targetModule="Object", moduleItemId=objId)

#
# set standardbild
# AssetUploader l.726

r = self.client.mk_asset_standardbild2(objId=objId, mulId=mulId)
