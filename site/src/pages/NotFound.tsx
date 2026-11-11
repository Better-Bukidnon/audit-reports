import { useT, useTitle } from '../i18n';
import { Link } from '../router';
import { ui } from '../ui';

export function NotFound() {
  const t = useT();
  useTitle(t('notFoundTitle'));
  return (
    <div className={ui.pageHead}>
      <h1 className={ui.h1}>{t('notFoundTitle')}</h1>
      <p className={ui.lede}>{t('notFoundP')}</p>
      <p className="mt-4">
        <Link to="/">{t('notFoundHome')}</Link>
      </p>
    </div>
  );
}
