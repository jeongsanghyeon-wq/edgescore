import { useState, useEffect, useCallback } from "react";

// ── CONFIG (자동 감지) ──
// Tailscale IP를 여기에 한 번만 입력하세요 (맥미니에서 tailscale ip -4 로 확인)
const TAILSCALE_IP = "100.84.228.61"; // ← 본인 맥미니 Tailscale IP로 변경
const RT_PORT = 5000;

// 자동 감지: localhost/127.0.0.1/맥미니LAN IP → 로컬, 그 외 → Tailscale
const _host = window.location.hostname;
const _isLocal = ["localhost","127.0.0.1","0.0.0.0",""].includes(_host)
  || _host.startsWith("192.168.") || _host.startsWith("10.");
const API = _isLocal
  ? `http://${_host || "localhost"}:${RT_PORT}`
  : `http://${TAILSCALE_IP}:${RT_PORT}`;

const TICK = 5000;
const RM = { BULL:{icon:"📈",label:"상승장",c:"#22c55e"}, SIDE:{icon:"➡️",label:"보합장",c:"#eab308"}, BEAR:{icon:"📉",label:"하락장",c:"#ef4444"} };
const fmt = n => n?.toLocaleString("ko-KR") ?? "0";
const pct = n => (n>=0?"+":"") + (n*100).toFixed(2) + "%";
const ec = e => e>=80?"#22c55e":e>=70?"#3b82f6":e>=60?"#eab308":e>=40?"#f97316":"#ef4444";
// [개선3] AbortController — 탭 이동/언마운트 시 중복 호출 방지
async function api(p,signal){try{const r=await fetch(`${API}/api${p}`,{signal});return r.ok?await r.json():null}catch{return null}}

// ── 반응형 훅 ──
function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(window.innerWidth < breakpoint);
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < breakpoint);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [breakpoint]);
  return isMobile;
}

// ── Sparkline ──
function Spark({data,color,w=120,h=32}){
  if(!data||data.length<2)return <div style={{width:w,height:h}}/>;
  const mn=Math.min(...data),mx=Math.max(...data),rg=mx-mn||1;
  const pts=data.map((v,i)=>`${(i/(data.length-1))*w},${h-((v-mn)/rg)*(h-4)-2}`).join(" ");
  return <svg width={w} height={h} style={{display:"block"}}><polyline points={pts} fill="none" stroke={color||(data.at(-1)>=data[0]?"#22c55e":"#ef4444")} strokeWidth="1.5" strokeLinejoin="round"/></svg>;
}

// ── Edge Gauge ──
function Gauge({score,size=40}){
  const r=size/2-4,circ=2*Math.PI*r,c=ec(score);
  return <div style={{position:"relative",width:size,height:size,display:"inline-block"}}>
    <svg width={size} height={size} style={{transform:"rotate(-90deg)"}}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1e293b" strokeWidth="3"/>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={c} strokeWidth="3" strokeDasharray={circ} strokeDashoffset={circ*(1-score/100)} strokeLinecap="round" style={{transition:"all 0.8s"}}/>
    </svg>
    <div style={{position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",fontSize:size>42?14:11,fontWeight:700,color:c}}>{score}</div>
  </div>;
}

// ── Capital Gauge ──
function CapitalGauge({gauge,mobile}){
  if(!gauge)return null;
  const {pct:p,floor_pct,danger,capital,floor}=gauge;
  const barPct=Math.min(Math.max(p*100,0),150),floorPos=floor_pct*100;
  return <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:mobile?12:16,marginBottom:12}}>
    <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
      <span style={{fontWeight:700,fontSize:mobile?11:13}}>💰 자본 게이지</span>
      <span style={{color:danger?"#ef4444":"#22c55e",fontWeight:600,fontSize:12}}>{(p*100).toFixed(1)}%</span>
    </div>
    <div style={{position:"relative",height:20,background:"#1e293b",borderRadius:10,overflow:"hidden"}}>
      <div style={{height:20,width:`${Math.min(barPct,100)}%`,background:danger?"linear-gradient(90deg,#ef4444,#f97316)":"linear-gradient(90deg,#22c55e,#3b82f6)",borderRadius:10,transition:"width 0.8s"}}/>
      <div style={{position:"absolute",top:-3,left:`${floorPos}%`,width:2,height:26,background:"#ef4444"}}/>
      <div style={{position:"absolute",top:-16,left:`${floorPos-2}%`,fontSize:8,color:"#ef4444",fontWeight:600}}>70%</div>
    </div>
    {!mobile&&<div style={{display:"flex",justifyContent:"space-between",marginTop:4,fontSize:9,color:"#64748b"}}><span>₩0</span><span>₩{fmt(floor)}</span><span>₩{fmt(capital)}</span></div>}
  </div>;
}

// ── Treemap ──
function Treemap({data,mobile}){
  if(!data?.length)return null;
  const total=data.reduce((s,d)=>s+d.value,0)||1;
  return <div style={{display:"flex",flexDirection:mobile?"column":"row",gap:4,marginBottom:12}}>
    {data.sort((a,b)=>b.value-a.value).map(d=>{
      const w=Math.max((d.value/total)*100,15);
      const bg=d.ret>=0.05?"#166534":d.ret>=0?"#14532d":d.ret>=-0.05?"#7f1d1d":"#991b1b";
      return <div key={d.sector} style={{width:mobile?"100%":`${w}%`,background:bg,borderRadius:6,padding:mobile?"10px 12px":8,display:"flex",flexDirection:mobile?"row":"column",justifyContent:mobile?"space-between":"center",alignItems:mobile?"center":"stretch",border:"1px solid #1e293b"}}>
        <div style={{fontWeight:700,fontSize:11,color:"#e2e8f0"}}>{d.sector}</div>
        <div style={{fontSize:mobile?16:18,fontWeight:800,color:d.ret>=0?"#4ade80":"#f87171"}}>{pct(d.ret)}</div>
        <div style={{fontSize:9,color:"#94a3b8"}}>₩{fmt(d.value)}</div>
      </div>;
    })}
  </div>;
}

// ── CorrMatrix ──
function CorrMatrix({data}){
  if(!data?.names?.length)return null;
  const {names,pairs}=data;
  const gc=(a,b)=>{const p=pairs.find(p=>(p.a===a&&p.b===b)||(p.a===b&&p.b===a));return p?p.corr:0;};
  const cc=v=>v>=0.7?"#ef4444":v>=0.3?"#f97316":v>=-0.3?"#94a3b8":"#3b82f6";
  return <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",fontSize:10}}>
    <thead><tr><th></th>{names.map(n=><th key={n} style={{padding:3,color:"#94a3b8",maxWidth:50}}>{n.slice(0,3)}</th>)}</tr></thead>
    <tbody>{names.map((n1,i)=><tr key={n1}><td style={{padding:3,color:"#94a3b8",fontWeight:600,whiteSpace:"nowrap",fontSize:9}}>{n1.slice(0,4)}</td>
      {names.map((n2,j)=>{const v=gc(n1,n2);return <td key={n2} style={{padding:3,textAlign:"center",background:i===j?"#1e293b":`${cc(v)}22`,color:cc(v),fontWeight:600,borderRadius:3,fontSize:9}}>{v.toFixed(1)}</td>})}</tr>)}</tbody>
  </table></div>;
}

// ── RotationMap ──
function RotationMap({data,mobile}){
  if(!data?.length)return <div style={{color:"#64748b",padding:20,textAlign:"center",fontSize:11}}>로딩...</div>;
  const W=mobile?320:480,H=mobile?200:280,P=40;
  const xs=data.map(d=>d.ret_1w),ys=data.map(d=>d.ret_1m);
  const xn=Math.min(...xs,-0.05),xx=Math.max(...xs,0.05),yn=Math.min(...ys,-0.1),yx=Math.max(...ys,0.1);
  const tx=v=>P+(v-xn)/(xx-xn)*(W-2*P),ty=v=>H-P-(v-yn)/(yx-yn)*(H-2*P);
  return <svg width={W} height={H} style={{background:"#0f172a",borderRadius:8,maxWidth:"100%"}}>
    <line x1={P} y1={ty(0)} x2={W-P} y2={ty(0)} stroke="#334155" strokeDasharray="4"/>
    <line x1={tx(0)} y1={P} x2={tx(0)} y2={H-P} stroke="#334155" strokeDasharray="4"/>
    {data.map(d=>{const x=tx(d.ret_1w),y=ty(d.ret_1m);const c=d.ret_1w>0&&d.ret_1m>0?"#22c55e":d.ret_1w<0&&d.ret_1m<0?"#ef4444":"#eab308";
      return <g key={d.sector}><circle cx={x} cy={y} r={mobile?6:8} fill={c} opacity={0.7}/><text x={x} y={y-10} textAnchor="middle" fill="#e2e8f0" fontSize={mobile?9:10} fontWeight="600">{d.sector}</text></g>})}
  </svg>;
}

// ── TradeCalendar ──
function TradeCalendar({data}){
  if(!data?.length)return null;
  const cells=[],today=new Date();
  for(let i=90;i>=0;i--){const d=new Date(today);d.setDate(d.getDate()-i);const ds=d.toISOString().slice(0,10);const e=data.find(t=>t.date===ds);const pnl=e?.pnl||0;
    cells.push(<div key={ds} title={`${ds}: ₩${fmt(pnl)}`} style={{width:8,height:8,background:pnl>0?"#166534":pnl<0?"#7f1d1d":"#1e293b",borderRadius:1.5}}/>);}
  return <div><div style={{fontSize:10,fontWeight:700,color:"#94a3b8",marginBottom:4}}>📅 거래 캘린더 (90일)</div>
    <div style={{display:"flex",flexWrap:"wrap",gap:1.5}}>{cells}</div></div>;
}

// ── EmotionThermo ──
function EmotionThermo({emotion,mobile}){
  if(!emotion)return null;
  const {score,level,emoji,advice,port_ret,consecutive_loss,circuit_active}=emotion;
  const barC=score<=25?"#22c55e":score<=50?"#eab308":score<=75?"#f97316":"#ef4444";
  return <div style={{background:score>50?"#450a0a":"#052e16",border:`1px solid ${barC}33`,borderRadius:8,padding:mobile?12:16}}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
      <span style={{fontSize:mobile?12:14,fontWeight:700}}>{emoji} {level}</span>
      <span style={{fontSize:mobile?20:24,fontWeight:800,color:barC}}>{score}°</span>
    </div>
    <div style={{height:6,background:"#1e293b",borderRadius:3,marginBottom:10}}>
      <div style={{height:6,width:`${score}%`,background:"linear-gradient(90deg,#22c55e,#eab308,#ef4444)",borderRadius:3,transition:"width 0.8s"}}/>
    </div>
    <div style={{fontSize:mobile?11:12,color:"#e2e8f0",marginBottom:6,fontWeight:600}}>{advice}</div>
    <div style={{display:"flex",gap:8,fontSize:9,color:"#94a3b8",flexWrap:"wrap"}}>
      <span>포트 {pct(port_ret)}</span><span>연속손실 {consecutive_loss}건</span>
      {circuit_active&&<span style={{color:"#ef4444"}}>🚨 서킷브레이커</span>}
    </div>
  </div>;
}

// ── 모바일 보유종목 카드 ──
function HoldingCard({h, onSell}){
  return <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12,marginBottom:8}} onClick={()=>onSell(h.ticker)}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
      <div><div style={{fontWeight:700,fontSize:13}}>{h.name}</div><div style={{fontSize:9,color:"#64748b"}}>{h.sector} · {h.hold_days}일째 · {h.shares}주</div></div>
      <Gauge score={h.edge} size={44}/>
    </div>
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8,marginBottom:8}}>
      <div><div style={{fontSize:9,color:"#64748b"}}>매수</div><div style={{fontSize:11}}>₩{fmt(h.buy_price)}</div></div>
      <div><div style={{fontSize:9,color:"#64748b"}}>현재</div><div style={{fontSize:11,color:h.ret>=0?"#22c55e":"#ef4444",fontWeight:600}}>₩{fmt(h.current_price)}</div></div>
      <div><div style={{fontSize:9,color:"#64748b"}}>손절</div><div style={{fontSize:11,color:"#f97316"}}>₩{fmt(h.sl_price)}</div></div>
    </div>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
      <div style={{display:"flex",gap:8,alignItems:"center"}}>
        <span style={{fontSize:16,fontWeight:800,color:h.ret>=0?"#22c55e":"#ef4444"}}>{pct(h.ret)}</span>
        <span style={{fontSize:11,color:h.pnl>=0?"#22c55e":"#ef4444"}}>{h.pnl>=0?"+":""}₩{fmt(h.pnl)}</span>
      </div>
      <div style={{display:"flex",gap:6,alignItems:"center"}}>
        <Spark data={h.price_history} w={60} h={18}/>
        {h.trail_active?<span style={{background:"#22c55e22",color:"#22c55e",padding:"2px 6px",borderRadius:4,fontSize:9,fontWeight:600}}>🔺추적</span>
          :h.atr_alerted?<span style={{background:"#ef444422",color:"#ef4444",padding:"2px 6px",borderRadius:4,fontSize:9,fontWeight:600}}>⚠손절</span>
          :<span style={{background:"#3b82f622",color:"#3b82f6",padding:"2px 6px",borderRadius:4,fontSize:9,fontWeight:600}}>보유</span>}
      </div>
    </div>
  </div>;
}

// ══════════════════════════════════════
// MAIN DASHBOARD
// ══════════════════════════════════════
export default function Dashboard(){
  const mobile = useIsMobile();
  const [conn,setConn]=useState(false),[st,setSt]=useState(null),[port,setPort]=useState(null),
    [watch,setWatch]=useState([]),[alerts,setAlerts]=useState([]),[perf,setPerf]=useState(null),
    [def,setDef]=useState(null),[kospi,setKospi]=useState(null),[risk,setRisk]=useState(null),
    [market,setMarket]=useState(null),[sentiment,setSentiment]=useState(null),[system,setSystem]=useState(null),
    [tab,setTab]=useState("portfolio"),[time,setTime]=useState(new Date()),[sellModal,setSellModal]=useState(null),
    [todayTrades,setTodayTrades]=useState(null),[account,setAccount]=useState(null),[trades,setTrades]=useState([]),
    [btParams,setBtParams]=useState({slip:2.0,pos:0.20,start:"20230101",end:"20260301"}),
    [btRunning,setBtRunning]=useState(false),[btResults,setBtResults]=useState([]),
    [btCurrent,setBtCurrent]=useState(null),[btError,setBtError]=useState(null);

  const fetchBtResults=useCallback(async()=>{
    try{const r=await fetch(`${API}/api/bt/results`);const d=await r.json();setBtResults(d.results||[]);}catch{}
  },[]);

  const fetchAll=useCallback(async(signal)=>{
    const s=await api("/status",signal);if(!s){setConn(false);return;}setConn(true);setSt(s);
    const [p,w,a,pf,d,k,r,m,se,sy,tt,ac,tr]=await Promise.all([api("/portfolio",signal),api("/watchlist",signal),api("/alerts",signal),api("/performance",signal),api("/defense",signal),api("/kospi",signal),api("/risk",signal),api("/market",signal),api("/sentiment",signal),api("/system",signal),api("/today_trades",signal),api("/account",signal),api("/trades",signal)]);
    if(p)setPort(p);if(w)setWatch(w.watchlist||[]);if(a)setAlerts(a.alerts||[]);if(pf)setPerf(pf);if(d)setDef(d);if(k)setKospi(k);if(r)setRisk(r);if(m)setMarket(m);if(se)setSentiment(se);if(sy)setSystem(sy);if(tt)setTodayTrades(tt);if(ac)setAccount(ac);if(tr)setTrades(tr.trades||[]);
  },[]);

  useEffect(()=>{const ac=new AbortController();fetchAll(ac.signal);fetchBtResults();const iv=setInterval(()=>{fetchAll(ac.signal);setTime(new Date())},TICK);return()=>{ac.abort();clearInterval(iv)}},[fetchAll,fetchBtResults]);
  const fetchSell=async t=>{const r=await api(`/sell_opinion/${t}`);if(r)setSellModal(r);};
  const r_=RM[st?.regime]||RM.SIDE, sm=port?.summary||{}, hld=port?.holdings||[], emo=sentiment?.emotion;

  // ── 연결 실패 ──
  if(!conn&&!st)return(<div style={{minHeight:"100vh",background:"#0a0e1a",display:"flex",alignItems:"center",justifyContent:"center",flexDirection:"column",color:"#e2e8f0",fontFamily:"monospace",padding:20}}>
    <div style={{fontSize:48,marginBottom:16}}>📊</div>
    <div style={{fontSize:20,fontWeight:700}}><span style={{color:"#3b82f6"}}>Edge</span><span style={{color:"#94a3b8"}}>Score</span></div>
    <div style={{color:"#64748b",margin:16,textAlign:"center"}}>RT 서버 연결 중...</div>
    <div style={{background:"#ef444422",border:"1px solid #ef444455",borderRadius:8,padding:"12px 20px",color:"#fca5a5",fontSize:12,textAlign:"center",maxWidth:320}}>
      연결 실패<br/><span style={{fontSize:10,color:"#94a3b8"}}>python rt.py 실행 확인<br/>API: {API || location.origin}:5000</span></div>
  </div>);

  const P = mobile ? 12 : 16; // padding

  return(<div style={{minHeight:"100vh",width:"100%",maxWidth:"100%",overflowX:"hidden",background:"#0a0e1a",color:"#e2e8f0",fontFamily:"'SF Mono','JetBrains Mono',monospace",fontSize:mobile?12:13}}>

    {/* ── 매도의견 모달 ── */}
    {sellModal&&<div style={{position:"fixed",inset:0,background:"#000000cc",zIndex:999,display:"flex",alignItems:"center",justifyContent:"center",padding:16}} onClick={()=>setSellModal(null)}>
      <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:12,padding:20,maxWidth:400,width:"100%"}} onClick={e=>e.stopPropagation()}>
        <div style={{display:"flex",justifyContent:"space-between",marginBottom:12}}>
          <span style={{fontSize:15,fontWeight:700}}>{sellModal.name} 매도 의견</span>
          <button onClick={()=>setSellModal(null)} style={{background:"none",border:"none",color:"#64748b",cursor:"pointer",fontSize:20}}>✕</button></div>
        <div style={{background:sellModal.action==="매도 권고"?"#ef444411":"#22c55e11",border:`1px solid ${sellModal.action==="매도 권고"?"#ef444433":"#22c55e33"}`,borderRadius:8,padding:14,textAlign:"center",marginBottom:14}}>
          <div style={{fontSize:22,fontWeight:800,color:sellModal.action==="매도 권고"?"#ef4444":"#22c55e"}}>{sellModal.action}</div></div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6,marginBottom:14}}>
          {[["현재가",`₩${fmt(sellModal.current_price)}`,"#e2e8f0"],["수익률",pct(sellModal.ret),sellModal.ret>=0?"#22c55e":"#ef4444"],["Edge",`${sellModal.edge}점`,ec(sellModal.edge)],["손절가",`₩${fmt(sellModal.sl_price)}`,"#f97316"]].map(([l,v,c],i)=>
            <div key={i} style={{background:"#0f172a",padding:8,borderRadius:6}}><div style={{color:"#64748b",fontSize:9}}>{l}</div><div style={{fontWeight:600,color:c,fontSize:13}}>{v}</div></div>)}
        </div>
        <div style={{fontSize:11}}><div style={{fontWeight:600,marginBottom:4}}>판단 근거:</div>
          {sellModal.reasons?.map((r,i)=><div key={i} style={{padding:"4px 0",borderBottom:"1px solid #1e293b",color:"#94a3b8"}}>• {r}</div>)}</div>
      </div>
    </div>}

    {/* ── 헤더 ── */}
    <div style={{background:"linear-gradient(135deg,#0f172a,#1e1b4b)",borderBottom:"1px solid #1e293b",padding:mobile?"8px 12px":"10px 20px"}}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:6}}>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <div style={{fontSize:mobile?15:18,fontWeight:800}}><span style={{color:"#3b82f6"}}>Edge</span><span style={{color:"#94a3b8"}}>Score</span></div>
          <div style={{background:r_.c+"22",border:`1px solid ${r_.c}55`,borderRadius:5,padding:"2px 8px",fontSize:10,color:r_.c,fontWeight:600}}>{r_.icon}{mobile?"":` ${r_.label}`}</div>
          {st?.circuit_active&&<div style={{background:"#ef444422",border:"1px solid #ef444455",borderRadius:5,padding:"2px 8px",fontSize:9,color:"#ef4444",fontWeight:600,animation:"pulse 2s infinite"}}>🚨{mobile?"":" 서킷브레이커"}</div>}
          {def?.econ_event?.today&&<div style={{background:"#eab30822",border:"1px solid #eab30855",borderRadius:5,padding:"2px 8px",fontSize:9,color:"#eab308",fontWeight:600}}>📆{mobile?"":" 경제이벤트 당일"}</div>}
          {!def?.econ_event?.today&&def?.econ_event?.tomorrow&&<div style={{background:"#3b82f622",border:"1px solid #3b82f655",borderRadius:5,padding:"2px 8px",fontSize:9,color:"#3b82f6",fontWeight:600}}>📆{mobile?"":" 내일 경제이벤트"}</div>}
        </div>
        <div style={{display:"flex",alignItems:"center",gap:mobile?8:14,fontSize:mobile?10:11,color:"#64748b"}}>
          {kospi&&<span style={{color:kospi.change>=0?"#22c55e":"#ef4444",fontWeight:600}}>{fmt(kospi.price)} {pct(kospi.change)}</span>}
          {emo&&<span style={{color:emo.score>50?"#ef4444":"#22c55e",fontWeight:600}}>{emo.emoji}{emo.score}°</span>}
          {account&&<span style={{background:account.mode==="모의투자"?"#1e3a5f":"#14532d",color:account.mode==="모의투자"?"#60a5fa":"#4ade80",padding:"2px 7px",borderRadius:8,fontSize:10,fontWeight:700}}>{account.mode_icon} {account.mode}</span>}
          {account&&account.deposit>0&&<span style={{color:"#fbbf24",fontWeight:600,fontSize:11}}>💰 {fmt(account.deposit)}원</span>}
          <span>{time.toLocaleTimeString("ko-KR",{hour:"2-digit",minute:"2-digit"})}</span>
          <div style={{width:7,height:7,borderRadius:"50%",background:conn?"#22c55e":"#ef4444",animation:"pulse 1.5s infinite"}}/>
        </div>
      </div>
    </div>

    {/* ── 탭 (모바일: 스크롤) ── */}
    <div style={{display:"flex",borderBottom:"1px solid #1e293b",background:"#0f172a",overflowX:"auto",WebkitOverflowScrolling:"touch"}}>
      {[{k:"portfolio",l:mobile?"📊":"📊 포트폴리오"},{k:"signals",l:mobile?"⚡":"⚡ 신호"},{k:"risk",l:mobile?"🛡️":"🛡️ 리스크"},{k:"alerts",l:mobile?`🔔${alerts.length}`:`🔔 알림(${alerts.length})`},{k:"performance",l:mobile?"📈":"📈 성과"},{k:"market",l:mobile?"🌍":"🌍 시장"},{k:"system",l:mobile?"⚙️":"⚙️ 시스템"},{k:"trades",l:mobile?"📋":"📋 체결내역"},{k:"backtest",l:mobile?"🧪":"🧪 백테스트"}].map(t=>
        <button key={t.k} onClick={()=>setTab(t.k)} style={{padding:mobile?"8px 12px":"9px 16px",background:tab===t.k?"#1e293b":"transparent",border:"none",borderBottom:tab===t.k?"2px solid #3b82f6":"2px solid transparent",color:tab===t.k?"#e2e8f0":"#64748b",cursor:"pointer",fontSize:mobile?12:11,fontWeight:600,fontFamily:"inherit",whiteSpace:"nowrap",minWidth:mobile?40:"auto"}}>{t.l}</button>)}
    </div>

    {/* ── 메인 ── */}
    <div style={{display:"flex",minHeight:"calc(100vh - 92px)"}}>
      <div style={{flex:1,overflow:"auto",padding:P, paddingBottom: mobile ? 20 : P}}>

        {/* ═══ 포트폴리오 ═══ */}
        {tab==="portfolio"&&<>
          {/* 카드 (모바일: 2열, PC: 3열) */}
          <div style={{display:"grid",gridTemplateColumns:mobile?"1fr 1fr":"repeat(3,1fr)",gap:mobile?8:10,marginBottom:8}}>
            {[{l:"평가금",v:`₩${fmt(sm.total_eval)}`,s:`원금 ₩${fmt(sm.total_invested)}`,c:"#3b82f6"},
              {l:"손익",v:`₩${fmt(sm.total_pnl)}`,s:pct(sm.total_ret||0),c:(sm.total_pnl||0)>=0?"#22c55e":"#ef4444"},
              {l:"가용현금",v:`₩${fmt(sm.available_cash)}`,s:`총자산 ₩${fmt(sm.capital)}`,c:"#f59e0b"}].map((c,i)=>
              <div key={i} style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:mobile?"10px":"12px 14px",borderLeft:`3px solid ${c.c}`}}>
                <div style={{fontSize:9,color:"#64748b",textTransform:"uppercase"}}>{c.l}</div>
                <div style={{fontSize:mobile?15:18,fontWeight:700,color:c.c,marginTop:1}}>{c.v}</div>
                {c.s&&<div style={{fontSize:9,color:"#94a3b8",marginTop:1}}>{c.s}</div>}
              </div>)}
          </div>
          <div style={{display:"grid",gridTemplateColumns:mobile?"1fr 1fr":"repeat(2,1fr)",gap:mobile?8:10,marginBottom:12}}>
            {[{l:"하한선",v:`₩${fmt(sm.floor)}`,s:`여유 ₩${fmt(sm.floor_remaining)}`,c:(sm.floor_remaining||0)>0?"#22c55e":"#ef4444"},
              {l:"보유",v:`${sm.count||0}개`,s:`트레일링 ${sm.trail_active_count||0}`,c:"#8b5cf6"}].map((c,i)=>
              <div key={i} style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:mobile?"10px":"12px 14px",borderLeft:`3px solid ${c.c}`}}>
                <div style={{fontSize:9,color:"#64748b",textTransform:"uppercase"}}>{c.l}</div>
                <div style={{fontSize:mobile?15:18,fontWeight:700,color:c.c,marginTop:1}}>{c.v}</div>
                {c.s&&<div style={{fontSize:9,color:"#94a3b8",marginTop:1}}>{c.s}</div>}
              </div>)}
          </div>

          <CapitalGauge gauge={risk?.gauge} mobile={mobile}/>

          {/* KOSPI 바 */}
          {kospi&&<div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:"10px 12px",marginBottom:12,display:"flex",alignItems:"center",gap:12}}>
            <div><div style={{fontSize:9,color:"#64748b"}}>KOSPI</div><div style={{fontSize:13,fontWeight:700,color:kospi.change>=0?"#22c55e":"#ef4444"}}>{fmt(kospi.price)}</div></div>
            <Spark data={kospi.history} color={kospi.change>=0?"#22c55e":"#ef4444"} w={mobile?180:350} h={28}/>
            <div style={{marginLeft:"auto",color:kospi.change>=0?"#22c55e":"#ef4444",fontSize:12,fontWeight:600}}>{pct(kospi.change)}</div>
          </div>}

          {/* 보유 종목 (모바일: 카드 / PC: 테이블) */}
          {mobile ? (
            <div>
              <div style={{fontWeight:700,fontSize:13,marginBottom:8}}>📌 보유 종목 <span style={{fontSize:9,color:"#64748b",fontWeight:400}}>탭→매도의견</span></div>
              {hld.length===0?<div style={{padding:24,textAlign:"center",color:"#64748b"}}>보유 종목 없음</div>:
                hld.map(h=><HoldingCard key={h.ticker} h={h} onSell={fetchSell}/>)}
            </div>
          ) : (
            <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,overflow:"hidden"}}>
              <div style={{padding:"10px 14px",borderBottom:"1px solid #1e293b",display:"flex",justifyContent:"space-between"}}>
                <span style={{fontWeight:700,fontSize:13}}>📌 보유 종목</span><span style={{fontSize:9,color:"#64748b"}}>클릭→AI매도의견</span></div>
              {hld.length===0?<div style={{padding:32,textAlign:"center",color:"#64748b"}}>보유 종목 없음</div>:
              <table style={{width:"100%",borderCollapse:"collapse"}}><thead><tr style={{borderBottom:"1px solid #1e293b",fontSize:9,color:"#64748b"}}>
                {["종목","Edge","매수가","현재가","수익률","손익","추이","손절","상태",""].map(h=><th key={h} style={{padding:"6px 10px",textAlign:h==="종목"?"left":"center",fontWeight:500}}>{h}</th>)}</tr></thead>
                <tbody>{hld.map((h,i)=><tr key={h.ticker} style={{borderBottom:"1px solid #1e293b11",background:i%2?"#0f172a33":"transparent",cursor:"pointer"}} onClick={()=>fetchSell(h.ticker)}>
                  <td style={{padding:"8px 10px",textAlign:"left"}}><div style={{fontWeight:600}}>{h.name}</div><div style={{fontSize:9,color:"#64748b"}}>{h.sector}·{h.hold_days}일</div></td>
                  <td style={{textAlign:"center"}}><Gauge score={h.edge}/></td>
                  <td style={{textAlign:"center",color:"#94a3b8",fontSize:11}}>₩{fmt(h.buy_price)}</td>
                  <td style={{textAlign:"center",fontWeight:600,color:h.ret>=0?"#22c55e":"#ef4444",fontSize:11}}>₩{fmt(h.current_price)}</td>
                  <td style={{textAlign:"center",fontWeight:700,fontSize:13,color:h.ret>=0?"#22c55e":"#ef4444"}}>{pct(h.ret)}</td>
                  <td style={{textAlign:"center",color:h.pnl>=0?"#22c55e":"#ef4444",fontSize:11}}>{h.pnl>=0?"+":""}₩{fmt(h.pnl)}</td>
                  <td style={{textAlign:"center"}}><Spark data={h.price_history} w={70} h={20}/></td>
                  <td style={{textAlign:"center",fontSize:9,color:"#f97316"}}>₩{fmt(h.sl_price)}</td>
                  <td style={{textAlign:"center"}}>{h.trail_active?<span style={{background:"#22c55e22",color:"#22c55e",padding:"2px 6px",borderRadius:4,fontSize:9,fontWeight:600}}>🔺추적</span>:h.atr_alerted?<span style={{background:"#ef444422",color:"#ef4444",padding:"2px 6px",borderRadius:4,fontSize:9,fontWeight:600}}>⚠손절</span>:<span style={{background:"#3b82f622",color:"#3b82f6",padding:"2px 6px",borderRadius:4,fontSize:9,fontWeight:600}}>보유</span>}</td>
                  <td><button onClick={e=>{e.stopPropagation();fetchSell(h.ticker)}} style={{background:"#3b82f622",border:"1px solid #3b82f644",color:"#3b82f6",borderRadius:4,padding:"2px 8px",fontSize:9,cursor:"pointer",fontFamily:"inherit"}}>💬</button></td>
                </tr>)}</tbody></table>}
            </div>
          )}

          {/* ── 오늘 체결내역 ── */}
          {todayTrades&&(todayTrades.buy_count>0||todayTrades.sell_count>0)&&(
            <div style={{background:'#111827',border:'1px solid #1e293b',borderRadius:8,padding:12,marginTop:10}}>
              <div style={{fontWeight:700,fontSize:12,marginBottom:8,color:'#e2e8f0'}}>📋 오늘 체결내역</div>
              <div style={{display:'flex',gap:16,marginBottom:8,flexWrap:'wrap'}}>
                <span style={{fontSize:11,color:'#64748b'}}>🟢 매수 <b style={{color:'#22c55e'}}>{todayTrades.buy_count}건</b></span>
                <span style={{fontSize:11,color:'#64748b'}}>🔴 매도 <b style={{color:'#ef4444'}}>{todayTrades.sell_count}건</b></span>
                {todayTrades.sell_count>0&&<span style={{fontSize:11,color:'#64748b'}}>손익 <b style={{color:todayTrades.total_pnl>=0?'#22c55e':'#ef4444'}}>{todayTrades.total_pnl>=0?'+':''}{todayTrades.total_pnl.toLocaleString()}원</b></span>}
                {todayTrades.sell_count>0&&<span style={{fontSize:11,color:'#64748b'}}>승률 <b style={{color:'#3b82f6'}}>{(todayTrades.win_rate*100).toFixed(0)}%</b></span>}
              </div>
              {todayTrades.sells.length>0&&<div style={{display:'flex',flexDirection:'column',gap:4}}>
                {todayTrades.sells.map((s,i)=><div key={i} style={{display:'flex',justifyContent:'space-between',fontSize:10,color:'#94a3b8',borderTop:'1px solid #1e293b',paddingTop:4}}>
                  <span>{s.name} ({s.ticker})</span>
                  <span style={{color:s.pnl>=0?'#22c55e':'#ef4444'}}>{s.pnl>=0?'+':''}{s.pnl.toLocaleString()}원 | {s.reason}</span>
                </div>)}
              </div>}
            </div>
          )}
        </>}

        {/* ═══ 신호 ═══ */}
        {tab==="signals"&&<><div style={{fontSize:13,fontWeight:700,marginBottom:10}}>⚡ AI 추천 종목</div>
          <div style={{display:"grid",gridTemplateColumns:mobile?"1fr":"repeat(3,1fr)",gap:10}}>
            {watch.map(w=><div key={w.ticker} style={{background:"#111827",border:`1px solid ${w.edge>=75?"#3b82f644":"#1e293b"}`,borderRadius:8,padding:12,borderLeft:`3px solid ${ec(w.edge)}`}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
                <div><div style={{fontWeight:700,fontSize:13}}>{w.name}</div><div style={{fontSize:9,color:"#64748b"}}>{w.sector}</div></div><Gauge score={w.edge} size={44}/></div>
              <div style={{display:"flex",justifyContent:"space-between",fontSize:11,color:"#94a3b8"}}><span>₩{fmt(w.price)}</span><span style={{color:w.change>=0?"#22c55e":"#ef4444",fontWeight:600}}>{pct(w.change)}</span></div>
              {w.guide&&<div style={{marginTop:6,background:"#0f172a",borderRadius:4,padding:6,fontSize:9,color:"#94a3b8"}}>
                💰 ₩{fmt(w.guide.entry_low)}~₩{fmt(w.guide.entry_high)} | 🎯₩{fmt(w.guide.target)} | 🛑₩{fmt(w.guide.sl_price)}</div>}
              {w.signal&&<div style={{marginTop:6,background:"#3b82f611",borderRadius:4,padding:3,fontSize:9,color:"#3b82f6",textAlign:"center"}}>⭐ 매수 신호</div>}
              {w.blocked&&<div style={{marginTop:6,background:"#ef444411",borderRadius:4,padding:3,fontSize:9,color:"#ef4444",textAlign:"center"}}>🚨 차단</div>}
            </div>)}</div></>}

        {/* ═══ 리스크 ═══ */}
        {tab==="risk"&&<>
          <div style={{fontSize:13,fontWeight:700,marginBottom:10}}>🛡️ 리스크 분석</div>
          <CapitalGauge gauge={risk?.gauge} mobile={mobile}/>
          <div style={{fontSize:11,fontWeight:700,color:"#94a3b8",marginBottom:6}}>📊 히트맵</div>
          <Treemap data={risk?.treemap} mobile={mobile}/>
          <div style={{display:"grid",gridTemplateColumns:mobile?"1fr":"1fr 1fr",gap:12}}>
            <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12}}>
              <div style={{fontSize:11,fontWeight:700,marginBottom:6}}>🔗 상관관계</div><CorrMatrix data={risk?.correlation}/></div>
            <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12}}>
              <EmotionThermo emotion={emo} mobile={mobile}/></div>
          </div></>}

        {/* ═══ 알림 ═══ */}
        {tab==="alerts"&&<>
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:10,flexWrap:"wrap",gap:4}}>
            <span style={{fontSize:13,fontWeight:700}}>🔔 알림 ({alerts.length}건)</span>
            {sentiment?.alert_response&&<span style={{fontSize:10,color:"#64748b"}}>대응률 {(sentiment.alert_response.rate*100).toFixed(0)}%</span>}</div>
          {alerts.map((a,i)=>{const bc={danger:"#ef4444",warning:"#eab308",success:"#22c55e",info:"#3b82f6",safe:"#6366f1"}[a.type]||"#3b82f6";
            return <div key={i} style={{background:`${bc}08`,borderLeft:`3px solid ${bc}`,borderRadius:6,padding:"8px 10px",display:"flex",alignItems:"center",gap:8,marginBottom:6}}>
              <span style={{fontSize:9,color:"#64748b",minWidth:32}}>{a.time}</span><span style={{fontSize:13}}>{a.icon}</span><span style={{fontSize:11,flex:1}}>{a.msg}</span></div>})}</>}

        {/* ═══ 성과 ═══ */}
        {tab==="performance"&&perf&&<>
          <div style={{display:"grid",gridTemplateColumns:mobile?"1fr":"repeat(3,1fr)",gap:10,marginBottom:12}}>
            {[{l:"이번 주",d:perf.week},{l:"이번 달",d:perf.month},{l:"누적",d:perf.all_time}].map(({l,d},i)=>
              <div key={i} style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:mobile?12:16,textAlign:"center"}}>
                <div style={{fontSize:10,color:"#64748b"}}>{l}</div><div style={{fontSize:mobile?18:22,fontWeight:700,color:d.total_pnl>=0?"#22c55e":"#ef4444",marginTop:2}}>₩{fmt(d.total_pnl)}</div>
                <div style={{fontSize:10,color:"#94a3b8",marginTop:2}}>{d.count}건·승률{(d.win_rate*100).toFixed(0)}%</div></div>)}
          </div>
          {perf.equity_curve?.length>1&&<div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12,marginBottom:12}}>
            <div style={{fontSize:11,fontWeight:700,marginBottom:4}}>📈 에쿼티 커브</div><Spark data={perf.equity_curve.map(e=>e.equity)} color="#3b82f6" w={mobile?300:700} h={mobile?50:80}/></div>}
          <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12,marginBottom:12}}><TradeCalendar data={perf.trade_calendar}/></div>
          {perf.rolling_20?.length>0&&<div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12,marginBottom:12}}>
            <div style={{fontSize:11,fontWeight:700,marginBottom:4}}>📊 이동 승률 (20건)</div><Spark data={perf.rolling_20.map(r=>r.win_rate)} color="#8b5cf6" w={mobile?300:700} h={mobile?40:60}/></div>}
        </>}

        {/* ═══ 시장 ═══ */}
        {tab==="market"&&<><div style={{display:"grid",gridTemplateColumns:mobile?"1fr":"1fr 1fr",gap:12}}>
          <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12}}>
            <div style={{fontSize:11,fontWeight:700,marginBottom:6}}>🔄 섹터 로테이션</div><RotationMap data={market?.rotation} mobile={mobile}/></div>
          <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12}}>
            <div style={{fontSize:11,fontWeight:700,marginBottom:6}}>🏦 외국인 순매수 (5일)</div>
            {market?.supply?.length>0?market.supply.sort((a,b)=>b.foreign_5d-a.foreign_5d).map((s,i)=>{const mx=Math.max(...market.supply.map(s=>Math.abs(s.foreign_5d)))||1;
              return <div key={i} style={{marginBottom:5}}><div style={{display:"flex",justifyContent:"space-between",fontSize:10,marginBottom:2}}>
                <span style={{color:"#94a3b8"}}>{s.name}</span><span style={{color:s.foreign_5d>=0?"#22c55e":"#ef4444",fontWeight:600}}>{s.foreign_5d>=0?"+":""}{fmt(s.foreign_5d)}</span></div>
                <div style={{height:3,background:"#1e293b",borderRadius:2}}><div style={{height:3,width:`${Math.abs(s.foreign_5d)/mx*100}%`,background:s.foreign_5d>=0?"#22c55e":"#ef4444",borderRadius:2}}/></div></div>})
              :<div style={{color:"#64748b",textAlign:"center",padding:16}}>로딩...</div>}</div></div></>}

        {/* ═══ 시스템 ═══ */}
        {tab==="system"&&system&&<>

          {/* ── ENGINE HALTED 배너 ── */}
          {system.critical_halt&&<div style={{background:"#7f1d1d",border:"1px solid #ef4444",borderRadius:8,padding:"10px 14px",marginBottom:12,display:"flex",alignItems:"center",gap:10}}>
            <span style={{fontSize:18}}>🚨</span>
            <div>
              <div style={{fontWeight:700,color:"#fca5a5",fontSize:13}}>ENGINE HALTED — 신규 매수 차단 중</div>
              <div style={{fontSize:10,color:"#fca5a5",marginTop:2}}>
                {Object.entries(system.critical_counts||{}).filter(([,v])=>v>0).map(([k,v])=>`${k}: ${v}회 실패`).join("  /  ")||"오류 누적"}
              </div>
              <div style={{fontSize:10,color:"#fca5a5aa",marginTop:2}}>텔레그램에서 /비상정지해제 로 복구하세요</div>
            </div>
          </div>}

          {/* ── RECONCILE 상태 카드 ── */}
          <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:"8px 12px",marginBottom:12,display:"flex",alignItems:"center",justifyContent:"space-between"}}>
            <span style={{fontSize:11,color:"#94a3b8"}}>🔍 마지막 잔고 대사</span>
            <span style={{fontSize:11,fontWeight:600,color:
              system.last_reconcile?.status==="ok"?"#22c55e":
              system.last_reconcile?.status==="issues"?"#f59e0b":
              system.last_reconcile?.status==="error"?"#ef4444":"#64748b"}}>
              {system.last_reconcile?.status==="ok"&&"✅ 전체 일치"}
              {system.last_reconcile?.status==="issues"&&`⚠️ ${system.last_reconcile.issues}건 수정됨`}
              {system.last_reconcile?.status==="error"&&"❌ 오류"}
              {system.last_reconcile?.status==="unknown"&&"⏳ 미확인"}
              {system.last_reconcile?.ts&&<span style={{color:"#475569",marginLeft:6,fontWeight:400}}>{system.last_reconcile.ts.slice(11,19)}</span>}
            </span>
          </div>

          <div style={{display:"grid",gridTemplateColumns:mobile?"1fr":"1fr 1fr",gap:12}}>
          <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12}}>
            <div style={{fontSize:11,fontWeight:700,marginBottom:6}}>📡 데이터 소스</div>
            {system.active_source&&<div style={{marginBottom:6,padding:"4px 8px",background:"#22c55e22",border:"1px solid #22c55e44",borderRadius:4,fontSize:10,color:"#22c55e"}}>🟢 현재 사용: <b>{system.active_source}</b></div>}
            {system.data_sources?.map((s,i)=><div key={i} style={{display:"flex",justifyContent:"space-between",padding:"5px 0",borderBottom:"1px solid #1e293b",fontSize:11,background:s.active?"#22c55e0a":"transparent",paddingLeft:s.active?6:0,borderLeft:s.active?"2px solid #22c55e":"none"}}>
              <span style={{color:s.active?"#22c55e":"#94a3b8"}}>{s.priority}. {s.icon} {s.name}{s.active?" ← 현재":""}</span><span style={{color:s.status==="ok"?"#22c55e":"#64748b",fontWeight:s.active?700:400}}>{s.status}{s.last_price?" ("+s.last_price.toLocaleString()+"원)":""}</span></div>)}</div>
          <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:12}}>
            <div style={{fontSize:11,fontWeight:700,marginBottom:6}}>⚙️ 파라미터</div>
            {system.current_params&&Object.entries(system.current_params).map(([k,v],i)=>v!=null&&<div key={i} style={{display:"flex",justifyContent:"space-between",padding:"3px 0",borderBottom:"1px solid #1e293b",fontSize:10}}>
              <span style={{color:"#94a3b8"}}>{k}</span><span style={{fontWeight:600}}>{typeof v==="number"?v.toFixed?.(4)??v:String(v)}</span></div>)}</div></div></>}

        {/* ═══ 체결내역 ═══ */}
        {tab==="trades"&&<>
          <div style={{fontSize:13,fontWeight:700,marginBottom:10}}>📋 체결내역</div>
          {account&&<div style={{display:"grid",gridTemplateColumns:mobile?"1fr 1fr":"1fr 1fr 1fr",gap:8,marginBottom:12}}>
            <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:10,textAlign:"center"}}>
              <div style={{fontSize:10,color:"#64748b",marginBottom:3}}>투자 모드</div>
              <div style={{fontSize:14,fontWeight:700,color:account.mode==="모의투자"?"#60a5fa":"#4ade80"}}>{account.mode_icon} {account.mode}</div>
            </div>
            <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:10,textAlign:"center"}}>
              <div style={{fontSize:10,color:"#64748b",marginBottom:3}}>주문가능 예수금</div>
              <div style={{fontSize:14,fontWeight:700,color:"#fbbf24"}}>💰 {fmt(account.deposit)}원</div>
            </div>
            <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:10,textAlign:"center"}}>
              <div style={{fontSize:10,color:"#64748b",marginBottom:3}}>연결 서버</div>
              <div style={{fontSize:10,fontWeight:600,color:"#94a3b8",wordBreak:"break-all"}}>{account.host}</div>
            </div>
          </div>}
          {trades.length===0?<div style={{textAlign:"center",color:"#64748b",padding:30}}>오늘 체결 내역이 없어요</div>:
          <div style={{overflowX:"auto"}}><table style={{width:"100%",borderCollapse:"collapse",fontSize:11}}>
            <thead><tr style={{borderBottom:"1px solid #1e293b",color:"#64748b",fontSize:10}}>
              <th style={{padding:"6px 4px",textAlign:"left"}}>시간</th>
              <th style={{padding:"6px 4px",textAlign:"left"}}>종목</th>
              <th style={{padding:"6px 4px",textAlign:"center"}}>구분</th>
              <th style={{padding:"6px 4px",textAlign:"right"}}>수량</th>
              <th style={{padding:"6px 4px",textAlign:"right"}}>단가</th>
              <th style={{padding:"6px 4px",textAlign:"right"}}>금액</th>
              <th style={{padding:"6px 4px",textAlign:"right"}}>손익</th>
            </tr></thead>
            <tbody>{trades.slice(0,50).map((t,i)=>{
              const isBuy=t.action==="BUY";
              const pnl=t.pnl||0;
              return <tr key={i} style={{borderBottom:"1px solid #1e293b11",background:i%2?"#0f172a33":"transparent"}}>
                <td style={{padding:"5px 4px",color:"#64748b"}}>{(t.timestamp||"").slice(11,16)}</td>
                <td style={{padding:"5px 4px",fontWeight:600}}>{t.name||t.ticker}</td>
                <td style={{padding:"5px 4px",textAlign:"center"}}><span style={{background:isBuy?"#22c55e22":"#ef444422",color:isBuy?"#22c55e":"#ef4444",padding:"2px 6px",borderRadius:4,fontWeight:700,fontSize:10}}>{isBuy?"매수":"매도"}</span></td>
                <td style={{padding:"5px 4px",textAlign:"right"}}>{fmt(t.shares)}주</td>
                <td style={{padding:"5px 4px",textAlign:"right"}}>{fmt(t.price)}원</td>
                <td style={{padding:"5px 4px",textAlign:"right"}}>{fmt((t.shares||0)*(t.price||0))}원</td>
                <td style={{padding:"5px 4px",textAlign:"right",color:pnl>=0?"#22c55e":"#ef4444",fontWeight:600}}>{pnl!==0?(pnl>=0?"+":"")+fmt(pnl)+"원":"-"}</td>
              </tr>;
            })}</tbody>
          </table></div>}
        </>}

      {/* ═══ 백테스트 ═══ */}
        {tab==="backtest"&&<>
          <div style={{fontSize:13,fontWeight:700,marginBottom:16}}>🔬 백테스트</div>

          {/* ── 데이터 다운로드 ── */}
          <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:14,marginBottom:12}}>
            <div style={{fontSize:11,fontWeight:700,color:"#94a3b8",marginBottom:10}}>📥 데이터 다운로드</div>
            <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
              <select value={btParams.start.slice(0,4)} onChange={e=>setBtParams(p=>({...p,start:e.target.value+"0101"}))}
                style={{background:"#0f172a",border:"1px solid #1e293b",color:"#e2e8f0",borderRadius:6,padding:"6px 10px",fontSize:12}}>
                {[2020,2021,2022,2023,2024].map(y=><option key={y} value={y}>{y}년부터</option>)}
              </select>
              <button onClick={async()=>{
                const r=await fetch(`${API}/api/bt/download`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({start:btParams.start,end:btParams.end})});
                const d=await r.json();
                setBtError(d.ok?"✅ 다운로드 시작 (백그라운드 실행 중...)":d.error||"실패");
              }} style={{background:"#1e3a5f",border:"1px solid #3b82f644",color:"#60a5fa",borderRadius:6,padding:"6px 14px",cursor:"pointer",fontSize:12,fontFamily:"inherit"}}>
                📥 다운로드
              </button>
              <span style={{fontSize:10,color:"#64748b"}}>yfinance로 코스피200 종목 데이터 캐싱</span>
            </div>
          </div>

          {/* ── 파라미터 설정 ── */}
          <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:14,marginBottom:12}}>
            <div style={{fontSize:11,fontWeight:700,color:"#94a3b8",marginBottom:10}}>⚙️ 파라미터 설정</div>
            <div style={{display:"grid",gridTemplateColumns:mobile?"1fr 1fr":"repeat(4,1fr)",gap:10,marginBottom:12}}>
              {[
                {label:"슬리피지 필터",key:"slip",step:0.5,min:1.0,max:5.0},
                {label:"최대 포지션 비중",key:"pos",step:0.05,min:0.05,max:0.50},
              ].map(({label,key,step,min,max})=>(
                <div key={key}>
                  <div style={{fontSize:10,color:"#64748b",marginBottom:4}}>{label}</div>
                  <div style={{display:"flex",alignItems:"center",gap:6}}>
                    <button onClick={()=>setBtParams(p=>({...p,[key]:Math.max(min,+(p[key]-step).toFixed(2))}))}
                      style={{background:"#1e293b",border:"1px solid #334155",color:"#e2e8f0",borderRadius:4,width:26,height:26,cursor:"pointer",fontSize:16,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"inherit"}}>−</button>
                    <span style={{fontSize:15,fontWeight:700,minWidth:38,textAlign:"center",color:"#e2e8f0"}}>{btParams[key]}</span>
                    <button onClick={()=>setBtParams(p=>({...p,[key]:Math.min(max,+(p[key]+step).toFixed(2))}))}
                      style={{background:"#1e293b",border:"1px solid #334155",color:"#e2e8f0",borderRadius:4,width:26,height:26,cursor:"pointer",fontSize:16,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"inherit"}}>+</button>
                  </div>
                </div>
              ))}
              <div>
                <div style={{fontSize:10,color:"#64748b",marginBottom:4}}>시작일</div>
                <input type="text" value={btParams.start} onChange={e=>setBtParams(p=>({...p,start:e.target.value}))}
                  style={{background:"#0f172a",border:"1px solid #1e293b",color:"#e2e8f0",borderRadius:6,padding:"5px 8px",fontSize:12,width:"100%",boxSizing:"border-box"}}/>
              </div>
              <div>
                <div style={{fontSize:10,color:"#64748b",marginBottom:4}}>종료일</div>
                <input type="text" value={btParams.end} onChange={e=>setBtParams(p=>({...p,end:e.target.value}))}
                  style={{background:"#0f172a",border:"1px solid #1e293b",color:"#e2e8f0",borderRadius:6,padding:"5px 8px",fontSize:12,width:"100%",boxSizing:"border-box"}}/>
              </div>
            </div>
            <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
              <button onClick={async()=>{
                setBtRunning(true);setBtError(null);setBtCurrent(null);
                try{
                  const r=await fetch(`${API}/api/bt/run`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(btParams)});
                  const d=await r.json();
                  if(d.ok){setBtCurrent(d.result);
                    const r2=await fetch(`${API}/api/bt/results`);const d2=await r2.json();setBtResults(d2.results||[]);}
                  else setBtError(d.error||"실행 실패");
                }catch(e){setBtError(String(e));}
                setBtRunning(false);
              }} disabled={btRunning}
                style={{background:btRunning?"#1e293b":"linear-gradient(135deg,#1d4ed8,#7c3aed)",border:"none",color:"#fff",borderRadius:6,padding:"8px 20px",cursor:btRunning?"not-allowed":"pointer",fontSize:12,fontWeight:700,fontFamily:"inherit"}}>
                {btRunning?"⏳ 실행 중 (최대 5분)...":"▶️ 백테스트 실행"}
              </button>
              <button onClick={async()=>{const r=await fetch(`${API}/api/bt/results`);const d=await r.json();setBtResults(d.results||[]);}}
                style={{background:"#1e293b",border:"1px solid #334155",color:"#94a3b8",borderRadius:6,padding:"8px 14px",cursor:"pointer",fontSize:12,fontFamily:"inherit"}}>
                🔄 이력 새로고침
              </button>
            </div>
            {btError&&<div style={{marginTop:8,padding:"6px 10px",background:btError.startsWith("✅")?"#14532d11":"#450a0a",border:`1px solid ${btError.startsWith("✅")?"#22c55e33":"#ef444433"}`,borderRadius:6,fontSize:11,color:btError.startsWith("✅")?"#4ade80":"#fca5a5"}}>{btError}</div>}
          </div>

          {/* ── 방금 실행 결과 ── */}
          {btCurrent&&<div style={{background:"#0f172a",border:"2px solid #3b82f644",borderRadius:8,padding:14,marginBottom:12}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
              <span style={{fontSize:12,fontWeight:700,color:"#60a5fa"}}>✅ 방금 실행 결과</span>
              <button onClick={async()=>{
                const r=await fetch(`${API}/api/bt/apply`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({slip:btCurrent.slip,pos:btCurrent.pos})});
                const d=await r.json();
                setBtError(d.ok?"✅ rt.py에 적용 완료! (런타임+소스 동시 반영)":d.error||"적용 실패");
              }} style={{background:"linear-gradient(135deg,#14532d,#166534)",border:"1px solid #22c55e44",color:"#4ade80",borderRadius:6,padding:"6px 16px",cursor:"pointer",fontSize:11,fontWeight:700,fontFamily:"inherit"}}>
                ✅ rt.py에 적용
              </button>
            </div>
            <div style={{display:"grid",gridTemplateColumns:mobile?"1fr 1fr":"repeat(4,1fr)",gap:8}}>
              {[
                {l:"전략수익률",v:`+${btCurrent.total_ret}%`,c:"#22c55e"},
                {l:"알파",v:`+${btCurrent.alpha}%`,c:"#3b82f6"},
                {l:"MDD",v:`${btCurrent.mdd}%`,c:"#ef4444"},
                {l:"승률",v:`${btCurrent.win_rate}%`,c:"#eab308"},
                {l:"총 매매",v:`${btCurrent.total_trades}건`,c:"#94a3b8"},
                {l:"슬리피지",v:`${btCurrent.slip}×`,c:"#8b5cf6"},
                {l:"최대비중",v:`${(btCurrent.pos*100).toFixed(0)}%`,c:"#8b5cf6"},
                {l:"기간",v:`${btCurrent.start?.slice(0,4)}~${btCurrent.end?.slice(0,4)}`,c:"#64748b"},
              ].map(({l,v,c},i)=>(
                <div key={i} style={{background:"#111827",borderRadius:6,padding:8,textAlign:"center"}}>
                  <div style={{fontSize:9,color:"#64748b"}}>{l}</div>
                  <div style={{fontSize:13,fontWeight:700,color:c,marginTop:2}}>{v}</div>
                </div>
              ))}
            </div>
          </div>}

          {/* ── 과거 이력 비교 테이블 ── */}
          {btResults.length>0&&<div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,overflow:"hidden",marginBottom:12}}>
            <div style={{padding:"10px 14px",borderBottom:"1px solid #1e293b"}}>
              <span style={{fontSize:12,fontWeight:700}}>📊 백테스트 이력 ({btResults.length}건)</span>
            </div>
            <div style={{overflowX:"auto"}}>
              <table style={{width:"100%",borderCollapse:"collapse",fontSize:11}}>
                <thead><tr style={{borderBottom:"1px solid #1e293b",color:"#64748b",fontSize:10}}>
                  {["날짜","기간","SLIP","POS","전략수익","알파","MDD","승률","매매","적용"].map(h=>(
                    <th key={h} style={{padding:"6px 8px",textAlign:h==="날짜"||h==="기간"?"left":"center",whiteSpace:"nowrap"}}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>{btResults.map((r,i)=>(
                  <tr key={i} style={{borderBottom:"1px solid #1e293b11",background:i%2?"#0f172a33":"transparent"}}>
                    <td style={{padding:"6px 8px",color:"#64748b",fontSize:10,whiteSpace:"nowrap"}}>{r.ts?.slice(0,8)}</td>
                    <td style={{padding:"6px 8px",fontSize:10,whiteSpace:"nowrap"}}>{r.start?.slice(0,4)}~{r.end?.slice(0,4)}</td>
                    <td style={{padding:"6px 8px",textAlign:"center",fontWeight:600}}>{r.slip}</td>
                    <td style={{padding:"6px 8px",textAlign:"center"}}>{(r.pos*100).toFixed(0)}%</td>
                    <td style={{padding:"6px 8px",textAlign:"center",color:"#22c55e",fontWeight:700}}>+{r.total_ret}%</td>
                    <td style={{padding:"6px 8px",textAlign:"center",color:"#3b82f6"}}>+{r.alpha}%</td>
                    <td style={{padding:"6px 8px",textAlign:"center",color:"#ef4444"}}>{r.mdd}%</td>
                    <td style={{padding:"6px 8px",textAlign:"center",color:"#eab308"}}>{r.win_rate}%</td>
                    <td style={{padding:"6px 8px",textAlign:"center"}}>{r.total_trades}</td>
                    <td style={{padding:"6px 8px",textAlign:"center"}}>
                      <button onClick={async()=>{
                        const res=await fetch(`${API}/api/bt/apply`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({slip:r.slip,pos:r.pos})});
                        const d=await res.json();
                        setBtError(d.ok?"✅ rt.py에 적용 완료!":d.error||"실패");
                      }} style={{background:"#22c55e22",border:"1px solid #22c55e44",color:"#22c55e",borderRadius:4,padding:"2px 8px",cursor:"pointer",fontSize:10,fontFamily:"inherit"}}>
                        적용
                      </button>
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </div>}

          {/* ── opt.py 실행 ── */}
          <div style={{background:"#111827",border:"1px solid #1e293b",borderRadius:8,padding:14}}>
            <div style={{fontSize:11,fontWeight:700,color:"#94a3b8",marginBottom:6}}>🧠 opt.py 실전 최적화</div>
            <div style={{fontSize:10,color:"#64748b",marginBottom:10}}>실거래 데이터(trade_history.db) 기반으로 파라미터 재최적화</div>
            <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
              <button onClick={async()=>{
                const r=await fetch(`${API}/api/opt/run`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({samples:400,seed:42,apply:false})});
                const d=await r.json();
                setBtError(d.ok?"✅ opt.py 실행 시작 (백그라운드)":d.error||"실패");
              }} style={{background:"#1e1b4b",border:"1px solid #4338ca44",color:"#a5b4fc",borderRadius:6,padding:"7px 14px",cursor:"pointer",fontSize:12,fontFamily:"inherit"}}>
                🧠 최적화 실행 (400회)
              </button>
              <button onClick={async()=>{
                const r=await fetch(`${API}/api/opt/run`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({samples:800,seed:42,apply:true})});
                const d=await r.json();
                setBtError(d.ok?"✅ opt.py 실행+자동적용 시작":d.error||"실패");
              }} style={{background:"#14532d",border:"1px solid #22c55e44",color:"#4ade80",borderRadius:6,padding:"7px 14px",cursor:"pointer",fontSize:12,fontFamily:"inherit"}}>
                🚀 최적화 + 자동 적용 (800회)
              </button>
            </div>
          </div>
        </>}

      </div>

      {/* ── 사이드바 (PC만) ── */}
      {!mobile&&<div style={{width:260,minWidth:260,borderLeft:"1px solid #1e293b",background:"#0f172a",padding:14,overflow:"auto",display:"flex",flexDirection:"column",gap:12}}>
        <div style={{background:"#111827",borderRadius:8,padding:10,border:"1px solid #1e293b"}}>
          <div style={{fontSize:10,fontWeight:700,color:"#94a3b8",marginBottom:6}}>🛡️ 안전장치</div>
          {[{l:"손절 체크",ok:true},{l:"매수 차단",ok:st?.circuit_active,w:true},{l:"자본 보호",ok:(sm.floor_remaining||0)>0},{l:"금요일 청산",ok:true},{l:"타임스탑",ok:def?.time_stop?.enabled},{l:"섹터제한",ok:def?.sector_limit?.enabled&&!(def?.sector_limit?.overloaded?.length>0)},{l:"주봉필터",ok:def?.weekly_trend?.enabled},{l:"이벤트감지",ok:!def?.econ_event?.today&&!def?.econ_event?.tomorrow}].map((i,j)=>
            <div key={j} style={{display:"flex",justifyContent:"space-between",fontSize:10,marginBottom:3}}><span style={{color:"#94a3b8"}}>{i.l}</span><span style={{color:i.w&&i.ok?"#ef4444":i.ok?"#22c55e":"#ef4444"}}>{i.w&&i.ok?"🚨":"✅"}</span></div>)}</div>
        {emo&&<div style={{background:emo.score>50?"#450a0a":"#052e16",borderRadius:8,padding:10,border:`1px solid ${emo.score>50?"#ef444433":"#22c55e33"}`}}>
          <div style={{display:"flex",justifyContent:"space-between",fontSize:10}}><span style={{color:"#94a3b8"}}>{emo.emoji} 감정온도</span><span style={{fontWeight:700,color:emo.score>50?"#ef4444":"#22c55e"}}>{emo.score}°</span></div></div>}
        <div style={{background:"#111827",borderRadius:8,padding:10,border:"1px solid #1e293b"}}>
          <div style={{fontSize:10,fontWeight:700,color:"#94a3b8",marginBottom:6}}>🔔 최근</div>
          {alerts.slice(-4).reverse().map((a,i)=><div key={i} style={{fontSize:9,color:"#94a3b8",padding:"3px 0",borderBottom:i<3?"1px solid #1e293b":"none"}}>{a.time} {a.icon} {a.msg?.substring(0,22)}...</div>)}</div>
        <div style={{background:"#111827",borderRadius:8,padding:10,border:"1px solid #1e293b"}}>
          <div style={{fontSize:10,fontWeight:700,color:"#94a3b8",marginBottom:6}}>🏭 섹터</div>
          {(()=>{const sec={};hld.forEach(h=>{sec[h.sector]=(sec[h.sector]||0)+h.current_price*h.shares});const tot=Object.values(sec).reduce((s,v)=>s+v,0)||1;const cs=["#3b82f6","#8b5cf6","#22c55e","#eab308","#ef4444"];
            return Object.entries(sec).sort((a,b)=>b[1]-a[1]).map(([s,v],i)=>{const p=v/tot;return <div key={s} style={{marginBottom:4}}>
              <div style={{display:"flex",justifyContent:"space-between",fontSize:9}}><span style={{color:p>0.4?"#ef4444":"#94a3b8"}}>{s}{p>0.4?"⚠":""}</span><span style={{color:"#64748b"}}>{(p*100).toFixed(0)}%</span></div>
              <div style={{height:3,background:"#1e293b",borderRadius:2}}><div style={{height:3,width:`${p*100}%`,background:p>0.4?"#ef4444":cs[i%5],borderRadius:2}}/></div></div>})})()}
        </div>
        <div style={{background:"#1e1b4b",borderRadius:8,padding:10,border:"1px solid #4338ca33"}}>
          <div style={{fontSize:10,fontWeight:700,color:"#a5b4fc",marginBottom:4}}>💬 안심</div>
          <div style={{fontSize:9,color:"#c7d2fe",lineHeight:1.6}}>바빠서 못 봐도 괜찮아요.<br/>1분마다 자동 체크 중.<br/>자본 70% 절대 보호.<br/>금요일 전체 정리 판단.</div></div>
      </div>}
    </div>
    <style>{`
      @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
      ::-webkit-scrollbar{width:4px}
      ::-webkit-scrollbar-track{background:#0a0e1a}
      ::-webkit-scrollbar-thumb{background:#1e293b;border-radius:2px}
      html{-webkit-text-size-adjust:100%}
      body{overscroll-behavior:none;margin:0;padding:0;overflow-x:hidden}
      #root{max-width:100%!important;width:100%!important;padding:0!important;margin:0!important}
    `}</style>
  </div>);
}
