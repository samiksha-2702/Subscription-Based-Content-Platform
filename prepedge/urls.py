from django.urls import include, path
from app1 import views
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home
    path('', views.index, name='index'),
    path('',views.home, name="home" ),

    # AI Recommendations
    path('ai/', include('ai_recommendations.urls')),
    path('ai-home/', views.ai_recommendation, name='ai'),

    # Main modules
    path('programming/', views.programming, name='programming'),
    path('company/', views.company, name='company'),
    path('expert/', views.expert_talks, name='expert'),
    path('communication/', views.communication, name='comm'),
    path('aptitude/', views.aptitude, name='questions'),

    # Auth
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Plans & Payment
    path('plans/', views.plans, name='plans'),
    path('payment/', views.payment, name='payment'),
    path('subscribe/', views.subscribe, name='subscribe'),

    # Python
    path('python/', views.python_info, name='python_info'),
    path('python/basics/', views.python_basics, name='pythonbasics'),
    path('python/control-flow/', views.control_flow, name='control_flow'),
    path('python/functions/', views.python_functions, name='functionspython'),
    path('python/interview/', views.python_interview, name='pythoninterview'),
    path('python/comparison/', views.python_comparison, name='pythoncomparision'),
    path('python/libraries/', views.python_libraries, name='pythonlibraries'),
    path('python/practice-basics/', views.py_basics_practice, name='pybasicspractice'),
    path('python/practice-loops/', views.py_loop_practice, name='pylooppractice'),
    path('python/practice-functions/', views.py_function_practice, name='pyfunctionpractice'),
    path('python/test/', views.python_test, name='python_test'),

    # Java
    path('java/', views.java_info, name='javainfo'),
    path('java-basics/', views.java_basics, name='java_basics'),
    path('java-control/', views.java_control, name='java_control'),
    path('java-oop/', views.java_oop, name='java_oop'),
    path('java-interview/', views.java_interview, name='java_interview'),
    path('java-vs-python/', views.java_vs_python, name='java_vs_languages'),
    path('springboot/', views.springboot, name='springboot'),
    path('java-basic-practice/', views.java_basic_practice, name='java_basic_practice'),
    path('java-loop-practice/', views.java_loop_practice, name='java_loop_practice'),
    path('java-oop-practice/', views.java_oop_practice, name='java_oop_practice'),
    path('java-test/', views.java_test, name='java_test'),

    # C++
    path('cpp/', views.cpp_info, name='cppinfo'),
    path('cpp-basics/', views.cpp_basics, name='cpp_basics'),
    path('cpp-control/', views.cpp_control, name='cpp_control'),
    path('cpp-oop/', views.cpp_oop, name='cpp_oop'),
    path('cpp-practice/', views.cpp_practice, name='cpp_practice'),
    path('cpp-test/', views.cpp_test, name='cpp_test'),

    # JavaScript
    path('js/', views.js_info, name='javasinfo'),
    path('js/basics/', views.js_basics, name='js_basics'),
    path('js/control/', views.js_control, name='js_control'),
    path('js/dom/', views.js_dom, name='js_dom'),
    path('js/es6/', views.js_es6, name='js_es6'),
    path('js/practice/', views.js_practice, name='js_practice'),
    path('js/test/', views.js_test, name='js_test'),

    # SQL
    path('sql/', views.sql_info, name='sql_info'),
    path('sql-basics/', views.sql_basics, name='sql_basics'),
    path('sql-queries/', views.sql_queries, name='sql_queries'),
    path('sql-joins/', views.sql_joins, name='sql_joins'),
    path('sql-advanced/', views.sql_advanced, name='sql_advanced'),
    path('sql-practice/', views.sql_practice, name='sql_practice'),
    path('sql-test/', views.sql_test, name='sql_test'),

    # DSA
    path('ds/', views.dsa_info, name='dsa_info'),
    path('dsa-basics/', views.dsa_basics, name='dsa_basics'),
    path('dsa-linear/', views.dsa_linear, name='dsa_linear'),
    path('dsa-sort/', views.dsa_sort, name='dsa_sort'),
    path('dsa-practice/', views.dsa_practice, name='dsa_practice'),
    path('dsa-test/', views.dsa_test, name='dsa_test'),

    # Expert sessions
    path('live-session-register/', views.live_session_register, name='live-session-regest'),
    path('view-talks/', views.view_talks, name='view_talks'),

    # Company blogs
    path('companies/', views.companies_blogs, name='companies_blogs'),
    path('google/', views.google, name='google'),
    path('amazon/', views.amazon, name='amazon'),
    path('microsoft/', views.microsoft, name='microsoft'),
    path('meta/', views.meta, name='meta'),

    path('interview-tips/', views.interview_tips, name='interview-tips'),
    path('resume-guide/', views.resume_guide, name='resume-guide'),
    path('tech-trends/', views.tech_trends, name='tech-trends'),
    path('experience-stories/', views.experience_stories, name='experience-stories'),

    # Communication
    path('time-management/', views.time_management, name='time_management'),
    path('teamwork/', views.teamwork, name='teamwork'),
    path('interview-skills/', views.interviewskills, name='interviewskills'),
    path('personality/', views.personality, name='personality'),
    path('verbal/', views.verbal, name='verbal'),
    path('non-verbal/', views.non_verbal, name='non_verbal'),
    path('listening/', views.listening, name='listening'),
    path('communication-quiz/', views.comm_quiz, name='comm_quiz'),

    # Aptitude
    path('aptitude/practice/', views.aptitude_practice, name='aptitude_practice'),
    path('aptitude/test/', views.aptitude_test, name='aptitude_test'),
    path('technical/practice/', views.technical_practice, name='technical_practice'),
    path('technical/test/', views.technical_test, name='technical_test'),
    path('interview/practice/', views.interview_practice, name='interview_practice'),
    path('interview/test/', views.interview_test, name='interview_test'),
    
   path('submit-test/<int:test_id>/', views.submit_test, name='submit_test'),
    path('result/<int:result_id>/', views.result_page, name='result'),
]