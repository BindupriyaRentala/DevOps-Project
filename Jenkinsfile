
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    triggers {
        pollSCM('H/2 * * * *')
    }

    stages {
        stage('Install Dependencies') {
            steps {
                echo "Installing Python Dependencies"
                bat 'python --version'
                bat 'python -m pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                echo "Running pytest"
                bat 'python -m pytest -q'
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Building Passkey Demo Docker Image"
                bat 'docker build -t passkey-demo:v1 .'
            }
        }

        
        stage('Docker Login') {
            steps {
                bat 'docker login -u rentalabindupriya -p bindupriya@19'
            }
        }


        stage('Push Docker Image to Docker Hub') {
            steps {
                echo "Tagging and Pushing Passkey Demo Image"

                bat 'docker tag passkey-demo:v1 rentalabindupriya/sample2026:passkey-demo'

                bat 'docker push rentalabindupriya/sample2026:passkey-demo'
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo "Deploying Passkey Demo to Kubernetes"

                bat 'kubectl get nodes'
                bat 'kubectl get secret passkey-demo-secret'

                bat 'kubectl apply -f k8s/deployment.yaml'
                bat 'kubectl apply -f k8s/service.yaml'

                bat 'kubectl set image deployment/passkey-demo passkey-demo=rentalabindupriya/sample2026:passkey-demo'

                bat 'kubectl rollout status deployment/passkey-demo --timeout=180s'
                bat 'kubectl get pods -l app=passkey-demo'
                bat 'kubectl get service passkey-demo'
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully!'
        }

        failure {
            echo 'Pipeline failed. Please check the logs.'
        }
    }
}
