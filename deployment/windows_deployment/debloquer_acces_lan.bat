@echo off
:: ==============================================================================
:: Script de Déblocage Automatique de l'Accès Réseau Câblé (LAN) — Windows Server
:: Ouvre le Port 8000, le mDNS 5353, active le PortProxy WSL2 et le profil Privé.
:: ==============================================================================
title DEBLOCAGE RESEAU CABLE (LAN) - EXAM SERVER
color 0b

echo ==============================================================================
echo    DEBLOCAGE DU SERVEUR D'EXAMEN POUR LE RESEAU CABLE (SWITCH / LAN)
echo ==============================================================================
echo.

:: 1. Vérification et élévation automatique des droits Administrateur
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Elevation des privileges Administrateur en cours...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c %~s0' -Verb RunAs"
    exit /b
)

echo [1/4] Configuration des regles du Pare-Feu Windows Defender...
netsh advfirewall firewall delete rule name="ExamQuiz Server LAN (Port 8000)" >nul 2>&1
netsh advfirewall firewall add rule name="ExamQuiz Server LAN (Port 8000)" dir=in action=allow protocol=TCP localport=8000 profile=any >nul
echo       -> Port 8000 (TCP) autorise sur TOUS les profils (Public, Prive, Domaine).

netsh advfirewall firewall delete rule name="ExamQuiz mDNS LAN (Port 5353)" >nul 2>&1
netsh advfirewall firewall add rule name="ExamQuiz mDNS LAN (Port 5353)" dir=in action=allow protocol=UDP localport=5353 profile=any >nul
echo       -> Port 5353 (UDP mDNS ZeroConf) autorise sur TOUS les profils.

netsh advfirewall firewall delete rule name="ExamQuiz ICMP Ping" >nul 2>&1
netsh advfirewall firewall add rule name="ExamQuiz ICMP Ping" dir=in action=allow protocol=icmpv4:8,any profile=any >nul
echo       -> Ping ICMP autorise (permet la decouverte et la cartographie reseau).
echo.

echo [2/4] Activation du relais Windows PortProxy vers Docker/WSL2...
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 >nul 2>&1
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=127.0.0.1 >nul
echo       -> Redirection de l'interface physique 0.0.0.0:8000 vers 127.0.0.1:8000 activee.
echo.

echo [3/4] Bascule du profil reseau Ethernet en mode Prive...
powershell -NoProfile -Command "Get-NetConnectionProfile | Where-Object { $_.InterfaceAlias -like '*Ethernet*' -or $_.InterfaceAlias -like '*Local*' } | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction SilentlyContinue" >nul 2>&1
echo       -> Interfaces reseau filaires passees en profil Prive (partage autorise).
echo.

echo [4/4] Adresses IP detectees sur ce serveur pour la salle d'examen :
echo ------------------------------------------------------------------------------
powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' -and $_.InterfaceAlias -notlike '*vEthernet*' } | ForEach-Object { Write-Host ('   -> Interface : ' + $_.InterfaceAlias.PadRight(25) + ' IP : http://' + $_.IPAddress + ':8000') -ForegroundColor Green }"
echo ------------------------------------------------------------------------------
echo.
echo ==============================================================================
echo   SUCCES : Le serveur est desormais accessible par toutes les machines du LAN !
echo   Donnez l'une des adresses ci-dessus (ou http://exam.local:8000) aux etudiants.
echo ==============================================================================
echo.
pause

