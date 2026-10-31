#pragma once

#include <stdint.h>

// Up to three 20 s join attempts with target-only scan diagnostics; reboots if all fail.
bool connectAresWiFi(const char *networkName, const char *networkPassword);
// Call from loop(): reboots if the link stays down longer than reboot_after_ms.
void maintainAresWiFi(uint32_t reboot_after_ms);
uint32_t aresWiFiDisconnects();
uint8_t aresWiFiLastReason();
