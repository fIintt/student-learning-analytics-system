// expires là thời điểm do frontend tính từ expires_in (giây) của API đăng nhập.
export function createSession(result, user, issuedAt = Date.now()) {
  const seconds = result.expires_in;
  if (
    typeof result.access_token !== 'string' ||
    !result.access_token ||
    typeof seconds !== 'number' ||
    !Number.isFinite(seconds) ||
    seconds <= 0
  ) {
    throw new Error('API đăng nhập trả token hoặc thời hạn phiên không hợp lệ.');
  }
  const expires = issuedAt + seconds * 1000;
  if (!Number.isFinite(expires) || expires <= Date.now())
    throw new Error('Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.');
  return { ...user, token: result.access_token, expires };
}
export function isSessionValid(session, now = Date.now()) {
  return (
    !!session &&
    typeof session.token === 'string' &&
    !!session.token &&
    typeof session.expires === 'number' &&
    Number.isFinite(session.expires) &&
    session.expires > now
  );
}
