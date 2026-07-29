(function(){
  'use strict';

  // Sidebar toggle
  var sidebar   = document.getElementById('admin-sidebar');
  var overlay   = document.getElementById('sidebar-overlay');
  var toggleBtn = document.getElementById('sidebar-toggle');

  if(toggleBtn){
    toggleBtn.addEventListener('click', function(){
      var isOpen = sidebar.classList.toggle('open');
      overlay.classList.toggle('show', isOpen);
      document.body.style.overflow = isOpen ? 'hidden' : '';
    });
  }
  function closeSidebar(){
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
  }
  if(overlay){ overlay.addEventListener('click', closeSidebar); }
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') closeSidebar(); });

  // Profile dropdown
  var profileBtn  = document.getElementById('profile-btn');
  var profileDrop = document.getElementById('profile-dropdown');
  if(profileBtn){
    profileBtn.addEventListener('click', function(e){
      e.stopPropagation();
      profileDrop.classList.toggle('open');
    });
    document.addEventListener('click', function(){
      profileDrop && profileDrop.classList.remove('open');
    });
  }

  // Active nav item — match longest prefix first
  var path = window.location.pathname;
  var items = Array.from(document.querySelectorAll('.nav-item[data-path]'));
  items.sort(function(a,b){ return b.getAttribute('data-path').length - a.getAttribute('data-path').length; });
  var matched = false;
  items.forEach(function(el){
    if(!matched && path.startsWith(el.getAttribute('data-path'))){
      el.classList.add('active');
      matched = true;
    }
  });

  // Sales Chart
  var canvas = document.getElementById('salesChart');
  if(canvas && window.Chart){
    var labels = window._chartLabels || ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var data   = window._chartData   || [0,0,0,0,0,0,0,0,0,0,0,0];

    new Chart(canvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets:[{
          label: 'Revenue (BDT)',
          data: data,
          borderColor: '#6366F1',
          backgroundColor: 'rgba(99,102,241,.08)',
          borderWidth: 2.5,
          pointBackgroundColor: '#6366F1',
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.4
        }]
      },
      options:{
        responsive: true,
        maintainAspectRatio: false,
        plugins:{
          legend:{ display:false },
          tooltip:{
            backgroundColor:'#fff',
            titleColor:'#0F172A',
            bodyColor:'#64748B',
            borderColor:'#E2E8F0',
            borderWidth:1,
            padding:10,
            callbacks:{ label: function(ctx){ return ' BDT' + ctx.parsed.y.toLocaleString(); } }
          }
        },
        scales:{
          x:{ grid:{ display:false }, ticks:{ color:'#94A3B8', font:{ size:11 } } },
          y:{ grid:{ color:'#F1F5F9' }, ticks:{ color:'#94A3B8', font:{ size:11 }, callback: function(v){ return 'BDT'+v; } } }
        }
      }
    });
  }
})();
