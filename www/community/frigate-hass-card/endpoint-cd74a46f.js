import{dq as t,d7 as n}from"./card-a5cfa285.js";const r=async(r,a,e)=>{if(!a.sign)return a.endpoint;let s;try{s=await t(r,a.endpoint,e)}catch(t){n(t)}return s?s.replace(/^http/i,"ws"):null};export{r as c};
