const links = document.querySelectorAll('a[href^="#"]');
links.forEach(link => link.addEventListener('click', e => {
  const target = document.querySelector(link.getAttribute('href'));
  if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
}));
const observer = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) entry.target.classList.add('is-visible'); }), { threshold: .14 });
document.querySelectorAll('.project,.about-layout,.process,.contact-top').forEach(el => { el.style.opacity = '0'; el.style.transform = 'translateY(24px)'; el.style.transition = 'opacity .8s ease, transform .8s ease'; observer.observe(el); });
const style = document.createElement('style'); style.textContent = '.is-visible{opacity:1!important;transform:translateY(0)!important}'; document.head.appendChild(style);
