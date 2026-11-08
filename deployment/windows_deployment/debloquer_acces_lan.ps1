<#
.SYNOPSIS
    Déblocage et configuration réseau pour serveur d'examen sur réseau câblé (LAN).
.DESCRIPTION
    Autorise le port 8000, 5353 (mDNS) et ICMP dans Windows Defender Firewall,
    configure le relais PortProxy pour la traversée WSL2/Docker et passe le profil réseau en Privé.
#>

#Requires -RunAsAdministrator

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "   DEBLOCAGE DU SERVEUR D'EXAMEN POUR LE RESEAU CABLE (LAN ETHERNET)" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Pare-Feu Windows
Write-Host "[1/4] Configuration des regles du Pare-Feu Windows..." -ForegroundColor Yellow
netsh advfirewall firewall delete rule name="ExamQuiz Server LAN (Port 8000)" | Out-Null
netsh advfirewall firewall add rule name="ExamQuiz Server LAN (Port 8000)" dir=in action=allow protocol=TCP localport=8000 profile=any | Out-Null
Write-Host "   -> Port 8000 (TCP) autorise sur tous les profils (Public, Prive)." -ForegroundColor Green

netsh advfirewall firewall delete rule name="ExamQuiz mDNS LAN (Port 5353)" | Out-Null
netsh advfirewall firewall add rule name="ExamQuiz mDNS LAN (Port 5353)" dir=in action=allow protocol=UDP localport=5353 profile=any | Out-Null
Write-Host "   -> Port 5353 (UDP mDNS) autorise sur tous les profils." -ForegroundColor Green

netsh advfirewall firewall delete rule name="ExamQuiz ICMP Ping" | Out-Null
netsh advfirewall firewall add rule name="ExamQuiz ICMP Ping" dir=in action=allow protocol=icmpv4:8,any profile=any | Out-Null
Write-Host "   -> Ping ICMP autorise." -ForegroundColor Green

# 2. PortProxy
Write-Host "`n[2/4] Activation du relais Windows PortProxy vers Docker..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 | Out-Null
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=127.0.0.1 | Out-Null
Write-Host "   -> Redirection 0.0.0.0:8000 vers 127.0.0.1:8000 activee." -ForegroundColor Green

# 3. Profil Privé
Write-Host "`n[3/4] Bascule du profil reseau Ethernet en mode Prive..." -ForegroundColor Yellow
Get-NetConnectionProfile | Where-Object { $_.InterfaceAlias -like '*Ethernet*' -or $_.InterfaceAlias -like '*Local*' } | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction SilentlyContinue
Write-Host "   -> Profil reseau fillaire configure en Prive." -ForegroundColor Green

# 4. Adresses IP
Write-Host "`n[4/4] Adresses IP detectees sur ce serveur :" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------------------------" -ForegroundColor Gray
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' -and $_.InterfaceAlias -notlike '*vEthernet*' } | ForEach-Object {
    $note = if ($_.IPAddress.StartsWith("169.254.")) { " [ATTENTION: APIPA sans DHCP]" } else { "" }
    Write-Host ("   -> " + $_.InterfaceAlias.PadRight(25) + " : http://" + $_.IPAddress + ":8000" + $note) -ForegroundColor Green
}
Write-Host "------------------------------------------------------------------------------" -ForegroundColor Gray
Write-Host "`nSUCCES : Le serveur est pret et accessible depuis les postes etudiants." -ForegroundColor Cyan

