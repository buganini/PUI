// The cookbook demonstrates optional auth; fixtures without auth connect directly.
module.exports = async function login(page) {
  if(!await page.locator('.pui-login').count())return;
  await page.getByLabel('Username',{exact:true}).fill('test');
  await page.getByLabel('Password',{exact:true}).fill('test123');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.locator('#pui-root').waitFor({state:'attached'});
};
