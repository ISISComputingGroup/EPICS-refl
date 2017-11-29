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
        setLatestGeniePath()
        echo "python path: ${env.PYTHON_PATH}"
      }
    }
    
    stage("Test BlockServer") {
      steps {
        script {
            env.GIT_COMMIT = bat(returnStdout: true, script: '@git rev-parse HEAD').trim()
            echo "git commit: ${env.GIT_COMMIT}"
            echo "git branch: ${env.BRANCH_NAME}"
        }
        
        bat """
            cd BlockServer
            set PYTHON_PATH=${env.PYTHON_PATH}
            %PYTHON_PATH%\\Python\\python.exe run_tests.py --output_dir ../test-reports
            """
      }
    }
    
// Commented because the database server tests have dependencies outside of inst_servers.
// Including being able to create a database.
// This needs to be unpicked.
/*    stage("Test DatabaseServer") {
      steps {        
        bat """
            cd DatabaseServer
            set PYTHON_PATH=${env.PYTHON_PATH}
            %PYTHON_PATH%\\Python\\python.exe run_tests.py --output_dir ../test-reports
            """
      }
    }
    */
    
    stage("Test ArchiverAccess") {
      steps {        
        bat """
            cd ArchiverAccess
            set PYTHON_PATH=${env.PYTHON_PATH}
            %PYTHON_PATH%\\Python\\python.exe run_tests.py --output_dir ../test-reports
            """
      }
    }
    
    stage("Test BlockServerToKafka") {
      steps {        
        bat """
            cd BlockServerToKafka
            set PYTHON_PATH=${env.PYTHON_PATH}
            %PYTHON_PATH%\\Python\\python.exe run_tests.py --output_dir ../test-reports
            """
      }
    }
        
    stage("Collate Unit Tests") {
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

def setLatestGeniePath() {
    def basePath = "P:/Kits\$/CompGroup/ICP/genie_python/"
    def fileContents = readFile basePath + 'LATEST_BUILD.txt'
    def pythonPath = basePath + "BUILD-$fileContents"
    env.PYTHON_PATH = pythonPath
}

