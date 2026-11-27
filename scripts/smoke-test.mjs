#!/usr/bin/env node
// Test de bout en bout du TD1 (pnpm smoke).
//
// Prérequis : pnpm infra:up puis pnpm dev (dans un autre terminal).
// 1. les trois services répondent sur /health ;
// 2. catalog publie un ping (POST /dev/ping) ;
// 3. stats le reçoit via Kafka en moins de 10 secondes (GET /stats/pings).
//
// Aucune dépendance : fetch est natif dans Node >= 18.
//
// On n'appelle jamais process.exit() : sous Windows, l'appeler pendant que
// fetch ferme ses connexions fait planter Node. On fixe process.exitCode
// et on laisse le programme se terminer de lui-même.

import { existsSync, readFileSync } from "node:fs";

const TIMEOUT_MS = 10_000;
const POLL_INTERVAL_MS = 300;

// Lecture minimale du .env racine (format CLE=valeur) pour connaître les ports.
function loadEnv(path = ".env") {
  const env = {};
  if (!existsSync(path)) return env;
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (match) env[match[1]] = match[2];
  }
  return env;
}

const env = { ...loadEnv(), ...process.env };
const services = {
  catalog: `http://localhost:${env.CATALOG_PORT ?? 3001}`,
  identity: `http://localhost:${env.IDENTITY_PORT ?? 3002}`,
  stats: `http://localhost:${env.STATS_PORT ?? 3003}`,
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function getJson(url, options = {}) {
  const response = await fetch(url, { signal: AbortSignal.timeout(5_000), ...options });
  if (!response.ok) throw new Error(`${url} -> HTTP ${response.status}`);
  return response.json();
}

async function main() {
  // 1. Santé des trois services
  console.log("1. Santé des services");
  for (const [name, baseUrl] of Object.entries(services)) {
    try {
      const body = await getJson(`${baseUrl}/health`);
      if (body.status !== "ok") throw new Error(JSON.stringify(body));
      console.log(`   ✔ ${name} (${baseUrl})`);
    } catch (error) {
      throw new Error(
        `${name} ne répond pas sur ${baseUrl}/health (${error.message}). pnpm dev est-il lancé ?`,
      );
    }
  }

  // 2. Publication d'un ping par catalog
  console.log("2. Publication d'un ping par catalog");
  let published;
  try {
    published = await getJson(`${services.catalog}/dev/ping`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: "smoke test" }),
    });
  } catch (error) {
    throw new Error(
      `publication impossible (${error.message}). Kafka est-il démarré (pnpm infra:up) ?`,
    );
  }
  console.log(
    `   ✔ eventId=${published.eventId} partition=${published.partition} offset=${published.offset}`,
  );

  // 3. Réception par stats (via Kafka) en moins de 10 s
  console.log("3. Réception par stats via Kafka");
  const start = Date.now();
  while (Date.now() - start < TIMEOUT_MS) {
    const stats = await getJson(`${services.stats}/stats/pings`).catch(() => null);
    const last = stats?.lastEvent;
    if (last?.eventId === published.eventId) {
      const elapsed = Date.now() - start;
      console.log(
        `   ✔ reçu en ${elapsed} ms : partition=${last.partition} offset=${last.offset} ` +
          `(total reçu : ${stats.count})`,
      );
      return;
    }
    await sleep(POLL_INTERVAL_MS);
  }
  throw new Error(`stats n'a pas reçu l'événement ${published.eventId} en ${TIMEOUT_MS / 1000} s.`);
}

try {
  await main();
  console.log("\n✅ Smoke test réussi : l'événement a traversé Kafka de catalog à stats.");
} catch (error) {
  console.error(`\n❌ ÉCHEC : ${error.message}`);
  process.exitCode = 1;
}
