import { useState } from "react";
import { useAccountStore } from "@/store/accountStore";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import { cabinetUrl, cloud, CloudError, pricingUrl } from "@/api/cloud";
import { computeFingerprint, detectDeviceName, detectPlatform } from "@/utils/fingerprint";
import styles from "./AccountTab.module.css";

/**
 * Вкладка «Аккаунт» в SettingsDialog.
 *
 * Два состояния:
 *   • Free (не активирован) — бейдж Free, прогресс месячной квоты,
 *     кнопка «Перейти на Pro» + collapsible «Уже купили? введите ключ».
 *   • Pro (активирован) — карточка профиля, статус, поля метрик,
 *     кнопка «Открыть личный кабинет».
 */
export function AccountTab() {
  const profile = useAccountStore((s) => s.profile);
  const subscription = useAccountStore((s) => s.subscription);
  const cache = useAccountStore((s) => s.cache);
  const isProActive = useAccountStore((s) => s.isProActive());
  const isOfflineTooLong = useAccountStore((s) => s.isOfflineTooLong());
  const signOut = useAccountStore((s) => s.signOut);

  if (profile && isProActive) {
    return (
      <ProState
        email={profile.email}
        displayName={profile.displayName}
        endsAt={subscription?.endsAt ?? ""}
        creditsRemaining={cache.creditsRemaining}
        offline={isOfflineTooLong}
        onSignOut={signOut}
      />
    );
  }

  return (
    <FreeState
      degraded={!!(subscription && !isProActive)}
      offline={isOfflineTooLong}
    />
  );
}

// ---------- Free state ----------

function FreeState({ degraded, offline }: { degraded: boolean; offline: boolean }) {
  const activate = useAccountStore((s) => s.activate);
  const pushToast = useAppStore((s) => s.pushToast);
  const cache = useAccountStore((s) => s.cache);
  const accessToken = useAccountStore((s) => s.accessToken);

  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const quotaTotal = 5;
  const remaining = Math.max(cache.aiQuotaRemaining === -1 ? quotaTotal : cache.aiQuotaRemaining, 0);
  const used = Math.max(quotaTotal - remaining, 0);
  const pct = Math.min((used / quotaTotal) * 100, 100);

  async function handleLinkEmail() {
    const trimmed = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setError(t.paywall.emailInvalid);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const fp = await computeFingerprint();
      const resp = await cloud.lookupByEmail({
        email: trimmed,
        fingerprint: fp,
        deviceName: detectDeviceName(),
        platform: detectPlatform(),
        appVersion: t.app.version,
      });
      activate({
        accessToken: resp.access_token,
        deviceId: resp.device.id,
        profile: {
          userId: resp.user.id,
          email: resp.user.email,
          displayName: resp.user.display_name,
        },
        subscription: {
          plan: resp.subscription.plan,
          endsAt: resp.subscription.ends_at,
          proActive: resp.subscription.pro_active,
        },
      });
      pushToast(t.paywall.emailLinked, "ok");
      setEmail("");
    } catch (err) {
      const ce = err as CloudError;
      const msg =
        ce.reason === "conflict"
          ? t.account.errors.deviceLimit
          : ce.reason === "network"
            ? t.account.errors.network
            : ce.message || t.account.errors.generic;
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  // Незарегистрированный юзер — accessToken'а нет ещё.
  const isAnonymous = !accessToken;

  return (
    <div className={styles.tab}>
      <div className={styles.heroFree}>
        <div className={styles.badgeRow}>
          <span className={isAnonymous ? styles.badgeMuted : styles.badgeFree}>
            {isAnonymous ? `НЕ ЗАРЕГИСТРИРОВАН · ${t.app.version}` : `FREE · ${t.app.version}`}
          </span>
          {degraded && (
            <span className={styles.badgeWarn}>{t.account.offlineDegraded}</span>
          )}
          {offline && !degraded && (
            <span className={styles.badgeMuted}>{t.account.offlineWarn}</span>
          )}
        </div>
        <p className={styles.heroLead}>
          {isAnonymous ? t.account.anonymousDescription : t.account.freeDescription}
        </p>

        {!isAnonymous && (
          <div className={styles.progressWrap}>
            <div className={styles.progressLabel}>
              {t.account.quotaLabel} <strong>{used}</strong> / {quotaTotal}
            </div>
            <div className={styles.progressTrack}>
              <div className={styles.progressBar} style={{ width: `${pct}%` }} />
            </div>
          </div>
        )}

        {isAnonymous && (
          <div className={styles.emailRow}>
            <input
              type="email"
              className={styles.emailInput}
              placeholder={t.paywall.emailPlaceholder}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={busy}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleLinkEmail();
              }}
            />
            <button
              type="button"
              className={styles.btnPrimary}
              onClick={() => void handleLinkEmail()}
              disabled={busy || !email.trim()}
            >
              {busy ? t.paywall.emailLinking : t.paywall.emailLink}
            </button>
          </div>
        )}

        {error && <div className={styles.errorBox}>{error}</div>}

        <div className={styles.heroActions}>
          <a
            href={pricingUrl()}
            target="_blank"
            rel="noreferrer noopener"
            className={isAnonymous ? styles.btnSecondary : styles.btnPrimary}
          >
            {t.account.upgradeToPro}
          </a>
        </div>
      </div>

    </div>
  );
}

// ---------- Pro state ----------

function ProState({
  email,
  displayName,
  endsAt,
  creditsRemaining,
  offline,
  onSignOut,
}: {
  email: string;
  displayName: string | null;
  endsAt: string;
  creditsRemaining: number;
  offline: boolean;
  onSignOut: () => void;
}) {
  const formatted = endsAt
    ? new Date(endsAt).toLocaleDateString("ru-RU", { year: "numeric", month: "long", day: "numeric" })
    : "—";

  return (
    <div className={styles.tab}>
      <div className={styles.heroPro}>
        <div className={styles.profileRow}>
          <div className={styles.avatar}>{(displayName || email).charAt(0).toUpperCase()}</div>
          <div className={styles.profileText}>
            <div className={styles.profileName}>{displayName || email}</div>
            <div className={styles.profileEmail}>{email}</div>
          </div>
          <span className={styles.badgePro}>PRO</span>
        </div>

        {offline && (
          <div className={styles.warnBanner}>{t.account.offlineWarn}</div>
        )}

        <dl className={styles.fields}>
          <dt>{t.account.fields.plan}</dt>
          <dd>Pro · 2 990 ₽/мес</dd>
          <dt>{t.account.fields.endsAt}</dt>
          <dd>{formatted}</dd>
          <dt>{t.account.fields.credits}</dt>
          <dd>{creditsRemaining}</dd>
          <dt>{t.account.fields.status}</dt>
          <dd>{offline ? t.account.fields.statusOffline : t.account.fields.statusActive}</dd>
        </dl>

        <div className={styles.heroActions}>
          <a
            href={cabinetUrl()}
            target="_blank"
            rel="noreferrer noopener"
            className={styles.btnPrimary}
          >
            {t.account.openCabinet}
          </a>
          <a
            href={cabinetUrl("/credits")}
            target="_blank"
            rel="noreferrer noopener"
            className={styles.btnSecondary}
          >
            {t.account.buyCredits}
          </a>
        </div>

        <button type="button" className={styles.btnLinkDanger} onClick={onSignOut}>
          {t.account.signOut}
        </button>
      </div>
    </div>
  );
}
