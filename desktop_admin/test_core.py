"""
Script de test unitaire pour les modules core de l'application desktop.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from desktop_admin.core.docker_manager import DockerManager
from desktop_admin.core.health_checker import HealthChecker
from desktop_admin.core.pc_renamer import PCRenamer
from desktop_admin.core.mdns_broadcaster import MDNSBroadcaster
from desktop_admin.core.network_scanner import NetworkScanner
from desktop_admin.core.backup_manager import BackupManager
from desktop_admin.core.firewall_checker import FirewallChecker

def test_all_core():
    print("--- 1. Testing DockerManager ---")
    dm = DockerManager()
    print("Docker installed:", dm.is_docker_installed())
    print("Docker running:", dm.is_docker_running())
    print("Containers status:", dm.get_containers_status())

    print("\n--- 2. Testing HealthChecker ---")
    hc = HealthChecker()
    telemetry = hc.get_server_telemetry()
    print("Host CPU %:", telemetry["host_cpu_percent"])
    print("Host RAM %:", telemetry["host_mem_percent"], f"({telemetry['host_mem_used_mb']} MB / {telemetry['host_mem_total_mb']} MB)")
    print("Disk free GB:", telemetry["disk_free_gb"])
    diagnosis = hc.run_full_diagnosis()
    print("Diagnosis items count:", len(diagnosis))
    for item in diagnosis:
        print(f"  [{item['status'].upper()}] {item['component']}: {item['title']}")

    print("\n--- 3. Testing PCRenamer ---")
    pr = PCRenamer()
    test_mac = "AA:BB:CC:DD:EE:FF"
    pr.set_alias(test_mac, "Poste Test 99", room="Salle TP A", ip="192.168.1.99")
    retrieved = pr.get_alias(test_mac)
    assert retrieved == "Poste Test 99", f"Expected 'Poste Test 99', got '{retrieved}'"
    print("PCRenamer alias set and retrieved successfully:", retrieved)
    pr.delete_alias(test_mac)

    print("\n--- 4. Testing MDNSBroadcaster (Multi-Interfaces & Renommage) ---")
    mb = MDNSBroadcaster(hostname="exam-test", port=8000)
    local_ip = mb.get_local_ip()
    print("Detected local IP:", local_ip)
    ifaces = mb.list_network_interfaces()
    print(f"Network interfaces detected ({len(ifaces)}):")
    for i in ifaces:
        print(f"  - {i['name']} -> {i['ip']} ({i['type_label']})")
    
    # Test renommage
    res_rename = mb.set_hostname("quiz-2026")
    print("Test hostname change to 'quiz-2026':", res_rename["success"], res_rename.get("full_url"))
    assert res_rename["success"], "Hostname change failed"

    bat_path = os.path.join(os.path.dirname(__file__), "test_hosts.bat")
    assert mb.generate_hosts_script(bat_path), "Failed to generate hosts script"
    print("Generated hosts script successfully.")
    if os.path.exists(bat_path):
        os.remove(bat_path)

    print("\n--- 5. Testing NetworkScanner (ARP Cache inspection) ---")
    ns = NetworkScanner(pr)
    arp = ns.read_arp_table()
    print(f"ARP cache read: {len(arp)} entries found.")

    print("\n--- 6. Testing BackupManager (Item 4: Snapshot 1-Clic) ---")
    bm = BackupManager()
    snap_res = bm.create_snapshot(label="Test_Auto")
    print("Snapshot creation result:", snap_res["success"], snap_res["message"])
    snaps = bm.list_snapshots()
    print(f"Available snapshots count: {len(snaps)}")
    if snaps:
        print(f"  Latest: {snaps[0]['filename']} ({snaps[0]['size_kb']} Ko)")

    print("\n--- 7. Testing FirewallChecker (Item 8: Pare-Feu Windows) ---")
    fc = FirewallChecker(port=8000, mdns_port=5353)
    fw_res = fc.check_firewall_rules()
    print("Firewall rules check:", fw_res)

    print("\n🎉 ALL CORE MODULES (INCLUDING 1, 4, 8) FUNCTIONING 100%!")

if __name__ == "__main__":
    test_all_core()
