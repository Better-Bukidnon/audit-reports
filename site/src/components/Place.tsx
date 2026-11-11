import { useT } from '../i18n';
import type { GovernmentMeta } from '../types';

/** "Municipality · 3rd District" in the reader's language. */
export function Place({ gov }: { gov: GovernmentMeta }) {
  const t = useT();
  const type = t(`type_${gov.type}`);
  if (!gov.district) return <>{type}</>;
  return (
    <>
      {type} · {t('district', { ord: gov.district, n: gov.district.replace(/\D/g, '') })}
    </>
  );
}
