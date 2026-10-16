// Web image resources remain restricted to the session HTTP route.
export function imageURL(value) {
  if(typeof value!=='string')return false;
  try {
    const u=new URL(value,location.href);
    return u.origin===location.origin && !u.hash && !u.username && !u.password &&
      /\/pui\/images\/[A-Za-z0-9_-]{32}$/.test(u.pathname) && /^\?mtime=-?\d+$/.test(u.search);
  } catch {return false;}
}
export const webResources = {valid: imageURL, url: value=>value};
