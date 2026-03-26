pipeline {
    agent any

    environment {
        EC2_USER       = 'ubuntu'
        EC2_IP         = branchIP()
        REMOTE_DIR     = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        BACKUP_DIR     = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}_old"
        POSTGRES_DB    = "postgres" 
        ODOO_PORT      = branchPort()
        COMPOSE_PROJECT_NAME = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        DB_PASS_CRED   = credentials('odoo-db-password')
    }

    stages {
        stage('Workspace Cleanup') {
            steps {
                deleteDir()
                checkout scm
            }
        }

        stage('Linting') {
            steps {
                echo "--- Analizando código ---"
                sh "pip install flake8 --break-system-packages || pip install flake8"
                sh "flake8 ./addons --count --select=E9,F63,F7,F82 --show-source --statistics || echo 'No addons found'"
            }
        }

        stage('Smart Unit Tests') {
            steps {
                script {
                    def commitMsg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
                    def targetModule = getTargetModule(commitMsg)
                    
                    if (targetModule) {
                        echo "--- EJECUTANDO TESTS DE LÓGICA PARA: ${targetModule} ---"
                        withEnv(["DB_PASS=${DB_PASS_CRED}"]) {
                            sh """
                                docker network create test-net-${BUILD_NUMBER} || true
                                
                                # Levantar DB temporal
                                docker run -d --name db-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    -e POSTGRES_PASSWORD=\$DB_PASS -e POSTGRES_USER=odoo -e POSTGRES_DB=postgres \
                                    postgres:16-alpine
                                
                                sleep 15

                                # Levantar Odoo temporal
                                docker run -d --name odoo-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    -e PGPASSWORD=\$DB_PASS \
                                    odoo:19.0 tail -f /dev/null

                                # Inyectar Addons
                                docker exec -u root odoo-test-${BUILD_NUMBER} mkdir -p /mnt/extra-addons
                                docker cp ./addons/. odoo-test-${BUILD_NUMBER}:/mnt/extra-addons/
                                
                                # Ejecutar Tests (FILTRANDO CHROME con --test-tags=at_install)
                                docker exec -u root odoo-test-${BUILD_NUMBER} sh -c "
                                    pip install --break-system-packages websocket-client && \
                                    odoo -d odoo_test \
                                    --db_host db-test-${BUILD_NUMBER} \
                                    --db_user odoo \
                                    --db_password=\\\$DB_PASS \
                                    --addons-path=/mnt/extra-addons \
                                    -i ${targetModule} --test-enable --stop-after-init --log-level=test --test-tags=at_install
                                "
                            """
                        }
                    } else {
                        echo "--- SALTANDO TESTS: No se detectó MOD:nombre_modulo en el commit ---"
                    }
                }
            }
            post {
                always {
                    sh "docker stop odoo-test-${BUILD_NUMBER} db-test-${BUILD_NUMBER} || true"
                    sh "docker rm odoo-test-${BUILD_NUMBER} db-test-${BUILD_NUMBER} || true"
                    sh "docker network rm test-net-${BUILD_NUMBER} || true"
                }
            }
        }

        stage('Deploy to EC2 with Snapshot') {
            steps {
                sshagent(['ec2-odoo-key']) { 
                    withEnv(["TARGET_DB_PASS=${DB_PASS_CRED}"]) {
                        sh """
                            echo "--- Preparando Snapshot y Backup en ${EC2_IP} ---"
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << 'EOF'
                                # 1. Crear snapshot SQL si el contenedor existe
                                if [ \$(docker ps -q -f name=${COMPOSE_PROJECT_NAME}-db-1) ]; then
                                    echo "Snapshotting DB..."
                                    docker exec ${COMPOSE_PROJECT_NAME}-db-1 pg_dump -U odoo -d postgres > /home/ubuntu/last_db_snapshot_${env.BRANCH_NAME}.sql
                                fi

                                # 2. Rotar carpetas de código
                                if [ -d ${REMOTE_DIR} ]; then
                                    rm -rf ${BACKUP_DIR}
                                    cp -r ${REMOTE_DIR} ${BACKUP_DIR}
                                fi
                                mkdir -p ${REMOTE_DIR}
EOF
                            # 3. Enviar nuevo código
                            scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                            
                            # 4. Levantar servicios
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << EOF
                                cd ${REMOTE_DIR}
                                echo 'POSTGRES_PASSWORD=${TARGET_DB_PASS}' > .env
                                echo 'ODOO_PORT=${ODOO_PORT}' >> .env
                                echo 'COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}' >> .env
                                
                                docker compose down --remove-orphans
                                docker compose up -d
                                sleep 15
                                
                                # Actualizar módulos en la DB de producción
                                docker compose exec -T -e PGPASSWORD='${TARGET_DB_PASS}' odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init --no-http
EOF
                        """
                    }
                }
            }
        }
    }

    post {
        success {
            script {
                def tagName = "deploy-${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
                sh "git tag ${tagName} && git push origin ${tagName}"
                echo "--- DESPLIEGUE OK Y TAG ${tagName} CREADO ---"
            }
        }
        failure { echo "--- PIPELINE FALLIDO ---" }
    }
}

@NonCPS
def getTargetModule(String msg) {
    def match = (msg =~ /MOD:([a-zA-Z0-9_]+)/)
    return match ? match[0][1] : null
}

def branchIP() { 
    return (env.BRANCH_NAME == 'main') ? '3.144.231.64' : '18.219.33.101' 
}

def branchPort() { 
    return (env.BRANCH_NAME == 'main') ? '8071' : '8070' 
}