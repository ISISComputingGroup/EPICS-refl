#!groovy

pipeline {

  // agent defines where the pipeline will run.
  agent {  
    label "ndw1757"
  }
  
  triggers {
    pollSCM('H/2 * * * *')
  }
  
  stages {  
    stage("Checkout") {
      steps {
        echo "Branch: ${env.BRANCH_NAME}"
        checkout scm
      }
    }
    
    stage("Build") {
      steps {
        script {
            env.GIT_COMMIT = bat(returnStdout: true, script: '@git rev-parse HEAD').trim()
            echo "git commit: ${env.GIT_COMMIT}"
            echo "git branch: ${env.BRANCH_NAME}"
        }
        
        bat """
            cd BlockServer
            C:\Python27\Scripts\virtualenv.exe my_python
            call my_python\Scripts\activate.bat
            call my_python\Scripts\pip.exe install xmlrunner
            call my_python\Scripts\pip.exe install six
            call my_python\Scripts\pip.exe install lxml
            C:\Python27\python.exe run_tests.py --output_dir ../test-reports
            """
      }
    }
    
    stage("Unit Tests") {
      steps {
        junit '**/test-reports/TEST-*.xml'
      }
    }
    
    
  }
  
  post {
    failure {
      step([$class: 'Mailer', notifyEveryUnstableBuild: true, recipients: 'icp-buildserver@lists.isis.rl.ac.uk', sendToIndividuals: true])
    }
  }
  
  // The options directive is for configuration that applies to the whole job.
  options {
    buildDiscarder(logRotator(numToKeepStr:'10'))
    timeout(time: 60, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
}

