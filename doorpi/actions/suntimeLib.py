# Formel von Dr. Roland Brodbeck, Calsky
# http://lexikon.astronomie.info/zeitgleichung/neu.html
# Uebertragung auf Python 3 von Alexander Klupp 2014-01-14
# Anpassung axk339 2017-10-31, 2025-09-27

import math
import time

class suntime:
    
    def __init__(self, geoBreite, geoLaenge) -> None:
        self.geoBreite = geoBreite
        self.geoLaenge = geoLaenge
        self.B         = math.radians(geoBreite)
        self.JD2000    = 2451545
        self.pi2       = 2*math.pi
        self.pi        = math.pi
        self.RAD       = math.pi/180

    def JulianischesDatum (self, Jahr, Monat, Tag, Stunde, Minuten, Sekunden):
        if (Monat <= 2):
            Monat = Monat + 12
            Jahr = Jahr - 1
        Gregor = (Jahr/400) - (Jahr/100) + (Jahr/4)  # Gregorianischer Kalender
        return 2400000.5 + 365 * Jahr - 679004 + Gregor \
               + math.floor(30.6001*(Monat + 1)) + Tag + Stunde/24 \
               + Minuten/1440 + Sekunden/86400

    def InPi(self, x):
        n = int(x/self.pi2)
        x = x - n*self.pi2
        if (x < 0):
            x += self.pi2
        return x

    def eps(self, T): # Neigung der Erdachse
        return self.RAD*(23.43929111 + (-46.8150*T - 0.00059*T**2 + 0.001813*T**3)/3600)

    def BerechneZeitgleichung(self, T):
        RA_Mittel = 18.71506921 + 2400.0513369*T +(2.5862e-5 - 1.72e-9*T)*T**2
        M  = self.InPi(self.pi2*(0.993133 + 99.997361*T))
        L  = self.InPi(self.pi2*(0.7859453 + M/self.pi2 + (6893*math.sin(M) + 72*math.sin(2*M) + 6191.2*T) / 1296e3))
        e  = self.eps(T)
        RA = math.atan(math.tan(L)*math.cos(e))
        if (RA < 0):
            RA += self.pi
        if (L > self.pi):
            RA += self.pi
        RA = 24*RA/self.pi2
        DK = math.asin(math.sin(e)*math.sin(L))
        #Damit 0 <= RA_Mittel < 24
        RA_Mittel = 24.0*self.InPi(self.pi2*RA_Mittel/24.0)/self.pi2
        dRA = RA_Mittel - RA
        if (dRA < -12.0):
            dRA += 24.0
        if (dRA > 12.0):
            dRA -= 24.0
        dRA = dRA* 1.0027379
        return dRA, DK

    def Suntime (self, event):
        # event 1 = Sonnenauf/-untergang        -50'
        # event 2 = Buergerliche Dämmerung      - 6°
        # event 3 = Nautische Dämmerung         -12°
        # event 4 = Astronomische Dämmerung     -18°
        
        lt = time.localtime()                      # Aktuelle, lokale Zeit als Tupel
        lt_jahr, lt_monat, lt_tag = lt[0:3]        # Datum
        lt_dst = lt[8]                             # Sommerzeit
    
        #if event == 1:
        #    print("Heute ist der {0:02d}.{1:02d}.{2:4d}" . format(lt_tag, lt_monat, lt_jahr))
        #    if lt_dst == 1:
        #        print("Sommerzeit")
        #    elif lt_dst == 0:
        #        print("Winterzeit")
        #    else:
        #        print("Keine Sommerzeitinformation vorhanden")
        
        T = (self.JulianischesDatum(lt_jahr, lt_monat, lt_tag, 12, 0, 0) - self.JD2000)/36525
        Zeitzone = lt_dst + 1
        Zeitgleichung, DK = self.BerechneZeitgleichung(T)
    
        #Minuten = Zeitgleichung*60
    
        if event == 2:
            h = -6*self.RAD
        elif event == 3:
            h = -12*self.RAD
        elif event == 4:
            h = -18*self.RAD
        else:
            h = -50.0/60.0*self.RAD
    
        Zeitdifferenz = 12*math.acos((math.sin(h) - math.sin(self.B)*math.sin(DK)) / (math.cos(self.B)*math.cos(DK)))/self.pi
    
        AufgangOrtszeit = 12 - Zeitdifferenz - Zeitgleichung
        UntergangOrtszeit = 12 + Zeitdifferenz - Zeitgleichung
        AufgangWeltzeit = AufgangOrtszeit - self.geoLaenge/15
        UntergangWeltzeit = UntergangOrtszeit - self.geoLaenge/15
    
        Aufgang = AufgangWeltzeit + Zeitzone
        if (Aufgang < 0):
            Aufgang += 24
        elif (Aufgang >= 24):
            Aufgang -= 24
    
        AM = round(Aufgang*60)/60 # minutengenau runden
    
        Untergang = UntergangWeltzeit + Zeitzone	
        if (Untergang < 0):
            Untergang += 24
        elif (Untergang >= 24):
            Untergang -= 24
    
        UM = round(Untergang*60)/60 # minutengenau runden
        
        AMh = int(math.floor(AM))
        AMm = int((AM - AMh)*60)
        UMh = int(math.floor(UM))
        UMm = int((UM - UMh)*60)
    
        #if event == 2:
        #    print("Buergerliche  Morgendaemmerung {0:02d}:{1:02d} Abenddaemmerung {2:02d}:{3:02d}". format(AMh, AMm, UMh, UMm))
        #elif event == 3:
        #    print("Nautische     Morgendaemmerung {0:02d}:{1:02d} Abenddaemmerung {2:02d}:{3:02d}". format(AMh, AMm, UMh, UMm))
        #elif event == 4:
        #    print("Astronomische Morgendaemmerung {0:02d}:{1:02d} Abenddaemmerung {2:02d}:{3:02d}". format(AMh, AMm, UMh, UMm))    
        #else:
        #    print("Sonnenaufgang {0:02d}:{1:02d} Sonnenuntergang {2:02d}:{3:02d}". format(AMh, AMm, UMh, UMm))
    
        return AMh, AMm, UMh, UMm
    
