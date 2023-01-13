ID, Label, Beispiel
#sechs
208, EM-Südsee/Australien VI, VI 45966 <2>
1090, EM-Ozeanien VI Dlg, VI Dlg 123 a
67, EM-Südsee/Australien VI K, VI K 123
73, EM-Südsee/Australien VI Nls, 
#sieben
64, EM-Südsee/Australien VII B, 
234, EM-Südsee/Australien VII F
65, EM-Südsee/Australien VII G
66, EM-Südsee/Australien VII I
#Acht
243, EM-Südsee/Australien VIII
68, EM-Südsee/Australien VIII B
1809, EM-Südsee/Australien VIII B Nls
69, EM-Südsee/Australien VIII C
70, EM-Südsee/Australien VIII D
71, EM-Südsee/Australien VIII F
#Neun
72, EM-Südsee/Australien IX C, IX C 123 a

VI Dlg => 1090
VI K => 67
VI Nls => 73
VI  => 208

Es gibt echte Signaturen. Aus diesen extrahieren wir das Schema. Das Schema bezeichnen wir mir 
den Buchstabenkombinationen am Anfang der Signatur. Also vor der fortlaufenden Nummer. Die 
Schemabezeichnung kann 1-3 solche Teile haben. Meinetwegen auch mehr.

Wenn wir das Schema haben, gucken wir die entsprechende ID in einem Lookup table nach

InvNrSchemata = {
#sechs
'VI Dlg': 1090,
'VI K': 67,
'VI Nls': 73
'VI': 208
#sieben
'VII B': 64,
'VII F': 234,
'VII G': 65,
'VII I': 66,
#acht
'VIII': 243
}