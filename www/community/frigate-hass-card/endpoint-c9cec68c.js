import{dp as t,d6 as n}from"./card-e5d55e5b.js";const r=async(r,a,e)=>{if(!a.sign)return a.endpoint;let s;try{s=await t(r,a.endpoint,e)}catch(t){n(t)}return s?s.replace(/^http/i,"ws"):null};export{r as c};