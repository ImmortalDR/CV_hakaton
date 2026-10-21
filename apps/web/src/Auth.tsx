import { useEffect, useRef, useState, type FormEvent } from "react";
import { Eye, EyeOff } from "./icons";
import { api, type Catalog, type User } from "./api";
type Mode = "login" | "register" | "forgot" | "reset" | "verify";
type Props = { verificationVersion: number; catalog: Catalog; onLogin: (user: User) => void; resetToken: string; onResetDone: () => void; };
function PasswordField({label,value,onChange,error,id,fresh}: {label:string;value:string;onChange:(v:string)=>void;error?:string;id:string;fresh:boolean}) {
  const [visible,setVisible]=useState(false);
  return <div className="field"><label htmlFor={id}>{label}</label><div className="password-control">
    <input id={id} name={id} type={visible?"text":"password"} autoComplete={fresh?"new-password":"current-password"} value={value} onChange={e=>onChange(e.target.value)} maxLength={128} aria-invalid={!!error} aria-describedby={error?`${id}-error`:undefined}/>
    <button type="button" className="password-toggle" onClick={()=>setVisible(!visible)} aria-label={`${visible?"Скрыть":"Показать"} ${label.toLowerCase()}`} aria-pressed={visible}>{visible?<EyeOff size={20}/>:<Eye size={20}/>}</button>
  </div>{error&&<small className="field-error" id={`${id}-error`}>{error}</small>}</div>;
}
export function Auth({verificationVersion,catalog,onLogin,resetToken,onResetDone}:Props) {
  const [mode,setMode]=useState<Mode>(resetToken?"reset":"login"),[email,setEmail]=useState(""),[password,setPassword]=useState(""),[repeat,setRepeat]=useState(""),[role,setRole]=useState("candidate"),[consent,setConsent]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(""),[fields,setFields]=useState<Record<string,string>>({}),[message,setMessage]=useState(""),[letter,setLetter]=useState(""),[cooldown,setCooldown]=useState(0);
  const form=useRef<HTMLFormElement>(null),pending=useRef(false);
  useEffect(()=>{if(resetToken){setMode("reset");setMessage("");setError("");}},[resetToken]);
  useEffect(()=>{if(!cooldown)return;const timer=window.setTimeout(()=>setCooldown(n=>Math.max(0,n-1)),1000);return()=>window.clearTimeout(timer);},[cooldown]);
  const changeMode=(next:Mode)=>{setMode(next);setError("");setFields({});setMessage("");setPassword("");setRepeat("");setLetter("");};
  const run=async(fn:()=>Promise<void>)=>{if(pending.current)return;pending.current=true;setBusy(true);setError("");try{await fn();}catch(e){setError(e instanceof TypeError?"Нет связи с сервером. Проверьте интернет и повторите. Введённые поля сохранены на этой странице.":e instanceof Error?e.message:"Не удалось выполнить действие. Повторите попытку.");}finally{pending.current=false;setBusy(false);}};
  const submit=(e:FormEvent)=>{
    e.preventDefault();const errors:Record<string,string>={};const fresh=mode==="register"||mode==="reset";
    if(mode!=="reset"&&(!email.trim()||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())))errors.email="Введите полный адрес почты, например name@example.org.";
    if(["register","reset","login"].includes(mode)&&!password)errors.password="Введите пароль.";
    if(fresh&&password.trim().length<10)errors.password="Не менее 10 символов без крайних пробелов.";
    if(fresh&&repeat!==password)errors.repeat="Пароли не совпадают. Проверьте оба поля с помощью кнопки показа пароля.";
    if(mode==="register"&&!consent)errors.consent="Для регистрации нужно согласие на обработку данных.";
    setFields(errors);setMessage("");setError("");
    if(Object.keys(errors).length){setError("Исправьте отмеченные поля — запрос ещё не отправлен.");window.setTimeout(()=>form.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus(),0);return;}
    void run(async()=>{
      if(mode==="register"){
        const r=await api<{message:string;demo_verification_url:string|null}>("/auth/register",{email:email.trim(),password,role,processing:consent});
        setMessage(r.message);setLetter(r.demo_verification_url??"");setMode("verify");setPassword("");setRepeat("");setCooldown(60);
      }else if(mode==="login"){onLogin(await api<User>("/auth/login",{email:email.trim(),password}));
      }else if(mode==="reset"){
        const r=await api<{message:string}>("/auth/reset-password",{token:resetToken,password});onResetDone();changeMode("login");setMessage(r.message);
      }else{const r=await api<{message:string}>(mode==="forgot"?"/auth/forgot-password":"/auth/resend-verification",{email:email.trim()});setMessage(r.message);setCooldown(60);}
    });
  };
  useEffect(()=>{if(verificationVersion){changeMode("login");}},[verificationVersion]);
  const fresh=mode==="register"||mode==="reset";
  const titles={login:"Добро пожаловать",register:"Создать аккаунт",forgot:"Восстановить доступ",reset:"Задайте новый пароль",verify:"Подтвердите почту"};
  return <><div className="eyebrow">Начните с одного шага</div><h2>{titles[mode]}</h2>
    <div className="segmented"><button disabled={busy} className={mode==="login"?"selected":""} onClick={()=>changeMode("login")}>Вход</button><button disabled={busy} className={mode==="register"?"selected":""} onClick={()=>changeMode("register")}>Регистрация</button></div>
    {mode==="register"&&<p>Создайте аккаунт → подтвердите почту → войдите. Профиль появится в подборе только после вашей публикации.</p>}
    {mode==="forgot"&&<p>Укажите почту аккаунта. Мы отправим ссылку для смены пароля; она действует 30 минут.</p>}
    {mode==="verify"&&<p>Проверьте входящие и папку «Спам». Ссылка подтверждения действует один час. Если в адресе опечатка, исправьте его и вернитесь к регистрации.</p>}
    {message&&<p className="notice" role="status">{message}</p>}{error&&<p className="auth-error" role="alert">{error}</p>}
    <form ref={form} onSubmit={submit} noValidate aria-busy={busy}><fieldset disabled={busy} className="auth-fields">
      {mode==="register"&&<div className="field"><label htmlFor="auth-role">Я на платформе как</label><select id="auth-role" value={role} onChange={e=>setRole(e.target.value)}><option value="candidate">Кандидат</option><option value="employer">Работодатель</option></select></div>}
      {mode!=="reset"&&<div className="field"><label htmlFor="auth-email">Электронная почта</label><input id="auth-email" type="email" autoComplete="email" inputMode="email" autoCapitalize="none" spellCheck={false} value={email} onChange={e=>setEmail(e.target.value)} aria-invalid={!!fields.email} aria-describedby={fields.email?"auth-email-error":undefined} placeholder="name@example.org"/>{fields.email&&<small className="field-error" id="auth-email-error">{fields.email}</small>}</div>}
      {["login","register","reset"].includes(mode)&&<PasswordField id="auth-password" label={mode==="reset"?"Новый пароль":"Пароль"} fresh={fresh} value={password} onChange={setPassword} error={fields.password}/>}
      {fresh&&<><p className="password-hint">От 10 до 128 символов. Сохраните пароль в менеджере паролей.</p><PasswordField id="auth-repeat" label="Повторите пароль" fresh value={repeat} onChange={setRepeat} error={fields.repeat}/></>}
      {mode==="register"&&<><label className="checkline"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)} aria-invalid={!!fields.consent}/><span>Согласен на обработку данных для профиля, тестирования и приглашений. Публикацию включу отдельно. В демо использую вымышленные данные.</span></label>{fields.consent&&<p className="field-error">{fields.consent}</p>}</>}
      <button className="full" disabled={busy||(["forgot","verify"].includes(mode)&&cooldown>0)}>{busy?"Отправляем запрос…":mode==="register"?"Создать аккаунт":mode==="login"?"Войти в кабинет":mode==="reset"?"Сохранить новый пароль":cooldown?`Повторить через ${cooldown} с`:mode==="verify"?"Отправить письмо повторно":"Отправить ссылку для смены пароля"}</button>
    </fieldset></form>
    <div className="auth-help">{mode!=="forgot"&&mode!=="register"&&<button className="text-button" disabled={busy} onClick={()=>changeMode("forgot")}>Забыли пароль?</button>}{mode==="login"&&<button className="text-button" disabled={busy} onClick={()=>changeMode("verify")}>Не пришло письмо подтверждения?</button>}{mode!=="login"&&<button className="text-button" disabled={busy} onClick={()=>changeMode("login")}>Вернуться ко входу</button>}</div>
    {letter&&<div className="demo-letter"><strong>Демонстрационное письмо</strong><p>Реальное письмо не отправлялось. Подтверждение имитируется.</p><button disabled={busy} onClick={()=>void run(async()=>{await api("/auth/verify",{token:letter.split("#verify=")[1]});changeMode("login");setMessage("Почта подтверждена. Войдите с указанным паролем.");})}>Подтвердить почту</button></div>}
    {catalog.demo&&mode==="login"&&<div className="demo-entry"><span>Посмотреть без регистрации</span><div>{(["candidate","employer"] as const).map(account=><button key={account} className="secondary" disabled={busy} onClick={()=>void run(async()=>onLogin(await api<User>("/auth/demo",{account})))}>{account==="candidate"?"Я кандидат":"Я работодатель"}</button>)}</div><small>Общие демоаккаунты. Не вводите персональные данные.</small></div>}
  </>;
}
