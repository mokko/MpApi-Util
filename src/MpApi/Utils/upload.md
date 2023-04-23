# Upload Excel Formst

## Zeilen
- Nach dem scandir gelaufen ist, kann man Zeilen löschen, dann werden die entsprechenden Dateien
  nicht hochgeladen. Oder man kann scandir erneut laufen lassen (vgl. scandir rerun)
  
## Scandir re-run
Wenn man scandir ein weiteres Mal laufen lässt, werden 
- alle Zeilen gelöscht, deren Dateien nicht mehr existieren. 
- Sollte es neue Dateien seit dem letzten 'scandir' geben, werden diese am Ende der Excel-Liste 
angefügt.
- Für existierende Zeilen, werden alle Spalten geprüft; leere Zellen werden erneut ausgefüllt.


## Spalten - Manuelles Eingreifen

- Dateiname: Wird automatisch während scandir ausgefüllt; nicht manuell ändern

- IdentNr: Wird automatisch während scandir durch Auswertung des Dateinamen ausgefüllt; kann
manuell überschrieben werden, wenn der eingebaute Logarithmus nicht richtig liegt.

- Assets mit diesem Dateinamen: Diese Spalte listet IDs von Assets, die diesen Dateinamen haben.
Wenn in Conf eine orgUnit angegeben wurde, werden nur Assets in diesem Bereich hier gelistet.
Wenn hier nach scandir bereits eine Nummer steht, zeigt das an, dass potenziell bereits das 
Asset-DS hochgeladen wurde oder vorliegendes neue Asset keinen distinkten Dateinamen besitzt.
Soll ein existierendes Asset-DS ignoriert werden, kann das Feld manuell gelöscht werden. Das 
Feld könnte auch manuell überschrieben werden, wenn das scandir nicht den richtigen Asset-DS
gefunden hätte.

- objId(s) aus RIA: Hier werden von scandir objIds von Datensätzen gelistet, die dieselbe IdentNr 
haben. Es können mehr als eine ID gelistet werden, wenn es mehrere DS mit dieser Signatur gibt.
Wenn eine orgUnit angegeben wurde, werden nur IDs aus diesem Bereich angezeigt.
Die IDs können manuell geändert werden. Einzelne IDs dürfen keine Semikolon haben.

- Teile objIds: Scandir listet hier IDs von Datensätzen für Teile des Objekts. Im Moment 
respektiert Teile objIds __nicht__ orgUnit, wenn diese existiert.

- Objekte-Link. Scandisk: Wenn in die beiden vorherigen Spalten ein eindeutiges Ergebnis geliefert 
haben, wird dieses hierhin kopiert. Up: Nur wenn diese Zelle mit einer ID ausgefüllt ist, wird der 
Upload ausgelöst.
